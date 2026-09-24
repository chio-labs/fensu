use std::fs;
use std::path::Path;
use std::process::{Command, Output};

use serde_json::Value;

pub(crate) const PYTHON_CONFIG: &str = "roots = [\"src/shop\"]\ntests = [\"tests\"]\n";
pub(crate) const RUST_CONFIG: &str = "[targets.rust]\nanalyzer = \"rust\"\nroots = [\"crates\"]\ntests = []\ntooling = []\nrule_packs = [\"rust\"]\nselect = [\"FPRS\"]\n";
pub(crate) const TYPESCRIPT_CONFIG: &str =
    "[targets.web]\nanalyzer = \"typescript\"\nroots = [\"src\"]\ntests = [\"tests\"]\n";
pub(crate) const SVELTE_CONFIG: &str =
    "[targets.web]\nanalyzer = \"svelte\"\nroots = [\"src\"]\ntests = [\"tests\"]\n";

pub(crate) const PYTHON_TEMPLATE: &str = r#"def {name}(orders, threshold):
    total = 0
    count = 0
    skipped = []
    for order in orders:
        if order.amount > threshold:
            total += order.amount
            count += 1{extra}
        else:
            skipped.append(order.identifier)
            {skip}(order, "below threshold")
    average = total / count if count else 0
    report = {"total": total, "count": count, "average": average, "skipped": skipped}
    {publish}(report, channel="orders")
    return report
"#;

pub(crate) const PYTHON_RENAMED: &str = r#"def summarize_customers(customers, limit):
    amount_sum = 1
    seen = 1
    ignored = []
    for customer in customers:
        if customer.balance > limit:
            amount_sum += customer.balance
            seen += 2
        else:
            ignored.append(customer.reference)
            record_skip(customer, "under limit")
    mean = amount_sum / seen if seen else 1
    result = {"sum": amount_sum, "seen": seen, "mean": mean, "ignored": ignored}
    publish_summary(result, channel="customers")
    return result
"#;

pub(crate) const PYTHON_UNRELATED: &str = r#"def restock_products(inventory, supplier):
    with supplier.session() as session:
        pending = [item for item in inventory if item.quantity < item.minimum]
        while pending:
            product = pending.pop()
            try:
                session.order(product.sku, product.minimum - product.quantity)
            except TimeoutError as error:
                raise RuntimeError(f"restock failed for {product.sku}") from error
            finally:
                session.flush()
    return {"supplier": supplier.name, "remaining": len(pending)}
"#;

pub(crate) const PYTHON_SHORT: &str =
    "def ship_order(order):\n    return dispatch(order.identifier, order.address)\n";

pub(crate) const RUST_TEMPLATE: &str = r#"pub fn {name}(orders: &[Order], threshold: u64) -> Summary {
    let mut total = 0;
    let mut count = 0;
    let mut skipped = Vec::new();
    for order in orders {
        if order.amount > threshold {
            total += order.amount;
            count += 1;{extra}
        } else {
            skipped.push(order.identifier.clone());
            {skip}(order, "below threshold");
        }
    }
    let average = if count > 0 { total / count } else { 0 };
    let report = Summary { total, count, average, skipped };
    {publish}(&report, "orders");
    report
}
"#;

pub(crate) const RUST_RENAMED: &str = r#"pub fn summarize_customers(customers: &[Customer], limit: u64) -> Totals {
    let mut amount_sum = 1;
    let mut seen = 1;
    let mut ignored = Vec::new();
    for customer in customers {
        if customer.balance > limit {
            amount_sum += customer.balance;
            seen += 2;
        } else {
            ignored.push(customer.reference.clone());
            record_skip(customer, "under limit");
        }
    }
    let mean = if seen > 1 { amount_sum / seen } else { 1 };
    let result = Totals { amount_sum, seen, mean, ignored };
    publish_summary(&result, "customers");
    result
}
"#;

pub(crate) const RUST_UNRELATED: &str = r#"pub fn restock_products(inventory: &mut Vec<Product>, supplier: &Supplier) -> usize {
    let mut remaining = 0;
    while let Some(product) = inventory.pop() {
        match supplier.order(&product.sku, product.minimum.saturating_sub(product.quantity)) {
            Ok(receipt) => println!("ordered {}", receipt.number),
            Err(error) => {
                eprintln!("restock failed for {}: {error}", product.sku);
                remaining += 1;
            }
        }
    }
    remaining
}
"#;

pub(crate) const RUST_SHORT: &str =
    "pub fn ship_order(order: &Order) -> bool {\n    dispatch(order.identifier, order.address)\n}\n";

pub(crate) const TYPESCRIPT_TEMPLATE: &str = r#"export function {name}(orders: Order[], threshold: number): Summary {
  let total = 0;
  let count = 0;
  const skipped: string[] = [];
  for (const order of orders) {
    if (order.amount > threshold) {
      total += order.amount;
      count += 1;{extra}
    } else {
      skipped.push(order.identifier);
      {skip}(order, "below threshold");
    }
  }
  const average = count > 0 ? total / count : 0;
  const report = { total: total, count: count, average: average, skipped: skipped };
  {publish}(report, "orders");
  return report;
}
"#;

pub(crate) const JAVASCRIPT_RENAMED: &str = r#"export function summarizeCustomers(customers, limit) {
  let amountSum = 1;
  let seen = 1;
  const ignored = [];
  for (const customer of customers) {
    if (customer.balance > limit) {
      amountSum += customer.balance;
      seen += 2;
    } else {
      ignored.push(customer.reference);
      recordSkip(customer, "under limit");
    }
  }
  const mean = seen > 1 ? amountSum / seen : 1;
  const result = { sum: amountSum, seen: seen, mean: mean, ignored: ignored };
  publishSummary(result, "customers");
  return result;
}
"#;

pub(crate) const TYPESCRIPT_UNRELATED: &str = r#"export async function restockProducts(inventory: Product[], supplier: Supplier): Promise<number> {
  let remaining = 0;
  while (inventory.length > 0) {
    const product = inventory.pop()!;
    try {
      const receipt = await supplier.order(product.sku, product.minimum - product.quantity);
      console.info(`ordered ${receipt.number}`);
    } catch (error) {
      console.error(`restock failed for ${product.sku}`, error);
      remaining += 1;
    }
  }
  return remaining;
}
"#;

pub(crate) const TYPESCRIPT_SHORT: &str =
    "export function shipOrder(order: Order): boolean {\n  return dispatch(order.identifier, order.address);\n}\n";

pub(crate) const PYTHON_EXTRA: &str = "\n            log_progress(count)";
pub(crate) const RUST_EXTRA: &str = "\n            log_progress(count);";
pub(crate) const TYPESCRIPT_EXTRA: &str = "\n      logProgress(count);";

pub(crate) const PYTHON_CALLS: (&str, &str) = ("record_skip", "publish_summary");
pub(crate) const PYTHON_OTHER_CALLS: (&str, &str) = ("note_skip", "emit_summary");
pub(crate) const WEB_CALLS: (&str, &str) = ("recordSkip", "publishSummary");
pub(crate) const WEB_OTHER_CALLS: (&str, &str) = ("noteSkip", "emitSummary");
pub(crate) const TYPE_ANNOTATIONS: &[&str] = &[": Order[]", ": number", ": Summary", ": string[]"];
pub(crate) const CONTRACT: &str = "from abc import ABC, abstractmethod\n\n\nclass Exporter(ABC):\n    @abstractmethod\n    def export_orders(self, orders, threshold):\n        raise NotImplementedError\n";
pub(crate) const BASE: &str = "from shop.contract import Exporter\n\n\nclass BaseExporter(Exporter):\n    def describe(self):\n        return \"exporter\"\n";
pub(crate) const GENERIC_BASE: &str = "from typing import Generic, TypeVar\n\nfrom shop.contract import Exporter\n\nT = TypeVar(\"T\")\n\n\nclass BaseExporter(Exporter, Generic[T]):\n    def describe(self):\n        return \"exporter\"\n";
pub(crate) const EXEMPTION: &str = "[[dupes.contract_exemptions]]\ncontract = \"src/shop/contract.py:Exporter\"\nforbidden_owners = [\"src/shop/base.py:BaseExporter\"]\npaths = [\"src/shop/exporters/*\"]\nreason = \"Every exporter must define the export contract itself.\"\n";
pub(crate) const CSV_EXPORTER: &str = "src/shop/exporters/csv.py";
pub(crate) const JSON_EXPORTER: &str = "src/shop/exporters/json.py";

pub(crate) fn copies() -> Vec<(&'static str, String)> {
    let summary = summary("");
    vec![
        ("src/shop/orders/summary.py", summary.clone()),
        ("src/shop/billing/summary.py", summary.clone()),
        ("scripts/summary.py", summary),
    ]
}

pub(crate) fn with_dupes(section: &str) -> String {
    format!("{PYTHON_CONFIG}tooling = [\"scripts\"]\n\n{section}")
}

pub(crate) fn function_body() -> String {
    seeded(PYTHON_TEMPLATE, "export_orders", "", PYTHON_CALLS).replace(
        "def export_orders(orders, threshold):",
        "def export_orders(self, orders, threshold):",
    )
}

pub(crate) fn method() -> String {
    function_body()
        .lines()
        .map(|line| format!("    {line}\n"))
        .collect()
}

pub(crate) fn exporter(prefix: &str, class_name: &str, bases: &str) -> String {
    format!("{prefix}\n\nclass {class_name}({bases}):\n{}", method())
}

pub(crate) fn exporter_repository(
    base: &str,
    csv: String,
    json: String,
) -> Vec<(&'static str, String)> {
    vec![
        ("src/shop/__init__.py", String::new()),
        ("src/shop/contract.py", CONTRACT.to_owned()),
        ("src/shop/base.py", base.to_owned()),
        (CSV_EXPORTER, csv),
        (JSON_EXPORTER, json),
    ]
}

pub(crate) fn direct(class_name: &str) -> String {
    exporter(
        "from shop.base import BaseExporter\n",
        class_name,
        "BaseExporter",
    )
}

pub(crate) fn exemption_config() -> String {
    format!("{PYTHON_CONFIG}\n[dupes]\n\n{EXEMPTION}")
}

pub(crate) fn rust_original() -> String {
    seeded(RUST_TEMPLATE, "summarize_orders", "", PYTHON_CALLS)
}

pub(crate) fn typescript_original() -> String {
    seeded(TYPESCRIPT_TEMPLATE, "summarizeOrders", "", WEB_CALLS)
}

pub(crate) fn without_types(source: &str) -> String {
    TYPE_ANNOTATIONS
        .iter()
        .fold(source.to_owned(), |text, annotation| {
            text.replace(annotation, "")
        })
}

pub(crate) fn summary(extra: &str) -> String {
    seeded(PYTHON_TEMPLATE, "summarize_orders", extra, PYTHON_CALLS)
}

pub(crate) fn ranked_files() -> Vec<(&'static str, String)> {
    vec![
        ("src/shop/orders/summary.py", summary("")),
        ("src/shop/billing/summary.py", summary("")),
        ("src/shop/reports/summary.py", summary("")),
        ("src/shop/inventory/restock.py", PYTHON_UNRELATED.to_owned()),
        ("src/shop/warehouse/restock.py", PYTHON_UNRELATED.to_owned()),
    ]
}

/// Fill a seeded template: `name`, an optional extra statement, and the two call targets.
pub(crate) fn seeded(template: &str, name: &str, extra: &str, calls: (&str, &str)) -> String {
    template
        .replace("{name}", name)
        .replace("{extra}", extra)
        .replace("{skip}", calls.0)
        .replace("{publish}", calls.1)
}

pub(crate) fn svelte_component(script: &str) -> String {
    format!("<script lang=\"ts\">\n{script}</script>\n\n<p>Orders</p>\n")
}

pub(crate) fn write(path: impl AsRef<Path>, contents: &str) {
    let path = path.as_ref();
    fs::create_dir_all(path.parent().expect("fixture parent")).expect("fixture directory");
    fs::write(path, contents).expect("fixture file");
}

pub(crate) fn write_files(root: &Path, files: &[(&str, String)]) {
    for (path, contents) in files {
        write(root.join(path), contents);
    }
}

pub(crate) fn run_dupes(root: &Path, arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_fensu"))
        .arg("dupes")
        .args(arguments)
        .current_dir(root)
        .env("FENSU_PYTHON", root.join("missing-python"))
        .env("NO_COLOR", "1")
        .output()
        .expect("native dupes process runs")
}

pub(crate) fn text(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes).into_owned()
}

pub(crate) fn json_report(output: &Output) -> Value {
    serde_json::from_slice(&output.stdout).expect("dupes JSON output")
}

/// Return every reported link as `(left path, right path, category)`, sorted.
pub(crate) fn links(report: &Value) -> Vec<(String, String, String)> {
    let mut found: Vec<(String, String, String)> = report["clusters"]
        .as_array()
        .expect("clusters array")
        .iter()
        .flat_map(cluster_links)
        .collect();
    found.sort();
    found
}

fn cluster_links(cluster: &Value) -> Vec<(String, String, String)> {
    let members = cluster["members"].as_array().expect("members array");
    let path = |slot: &Value| {
        members[usize::try_from(slot.as_u64().expect("member slot")).expect("slot fits")]["path"]
            .as_str()
            .expect("member path")
            .to_owned()
    };
    cluster["links"]
        .as_array()
        .expect("links array")
        .iter()
        .map(|link| {
            let (left, right) = (path(&link["left"]), path(&link["right"]));
            let (left, right) = (left.clone().min(right.clone()), left.max(right));
            (
                left,
                right,
                link["category"].as_str().expect("category").to_owned(),
            )
        })
        .collect()
}

/// Return the member paths of every reported cluster in rank order.
pub(crate) fn cluster_members(report: &Value) -> Vec<Vec<String>> {
    report["clusters"]
        .as_array()
        .expect("clusters array")
        .iter()
        .map(member_paths)
        .collect()
}

fn member_paths(cluster: &Value) -> Vec<String> {
    cluster["members"]
        .as_array()
        .expect("members array")
        .iter()
        .map(|member| {
            let forced = usize::from(member["forced"].as_bool().expect("forced flag"));
            let changed = usize::from(member["changed"].as_bool().expect("changed flag"));
            format!(
                "{}{}{}",
                member["path"].as_str().expect("member path"),
                ["", " [forced]"][forced],
                ["", " [changed]"][changed]
            )
        })
        .collect()
}

pub(crate) fn git(root: &Path, arguments: &[&str]) {
    let status = Command::new("git")
        .args([
            "-c",
            "user.name=Fensu Tests",
            "-c",
            "user.email=tests@example.com",
        ])
        .args(arguments)
        .current_dir(root)
        .output()
        .expect("git runs");
    assert!(
        status.status.success(),
        "git {arguments:?}: {}",
        text(&status.stderr)
    );
}
