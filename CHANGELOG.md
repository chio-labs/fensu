# Changelog

## [0.20.0](https://github.com/chio-labs/strata/compare/v0.19.0...v0.20.0) (2026-07-18)


### Features

* **init:** add memory opt-in ([83ed460](https://github.com/chio-labs/strata/commit/83ed4600ec06196d5db034a51c174cb1e09de248))
* **memory:** add bounded graph retrieval ([4176687](https://github.com/chio-labs/strata/commit/4176687a62e5afe066f4aba98585ce396bb96e4a))
* **memory:** add repository memory foundation ([49616a7](https://github.com/chio-labs/strata/commit/49616a789c6e3a1994742dac02bc3948344692b1))
* **memory:** add safe archival workflow ([2448fe4](https://github.com/chio-labs/strata/commit/2448fe4e244753c7ade340a6fb7b5bf7732f3c31))
* **memory:** classify Git visibility ([91f05b3](https://github.com/chio-labs/strata/commit/91f05b3eb2e89d20ec9d04a9b347879adb99f2d7))
* **memory:** harden private preview ([bd9874d](https://github.com/chio-labs/strata/commit/bd9874d9a7efdfa2c039138535f77859e7f9c397))
* **memory:** integrate source validation ([a41a90d](https://github.com/chio-labs/strata/commit/a41a90d52b15cfed3e949c212c7fb5758301ec75))
* **memory:** replace DuckDB with SQLite ([fd07e72](https://github.com/chio-labs/strata/commit/fd07e728acdf63f5777585a929685cf7567e0cfc))
* **skills:** synchronize project bundles ([e399914](https://github.com/chio-labs/strata/commit/e3999145a8b26df8b56433d19b9ad89b7e17776a))


### Bug Fixes

* **memory:** close proof database readers ([1a0a5bc](https://github.com/chio-labs/strata/commit/1a0a5bcfb640ad7f04ace2584f74884abd6baa97))
* **memory:** correct platform proof cases ([3f492de](https://github.com/chio-labs/strata/commit/3f492de3ac7db5652ce1511d683f35ca9da98ad7))
* **skills:** support Windows file replacement ([94a82dd](https://github.com/chio-labs/strata/commit/94a82dda1d40b0bc0fb7a137927b90efceaff61c))


### Performance Improvements

* **memory:** bulk publish DuckDB rows ([8de5c3e](https://github.com/chio-labs/strata/commit/8de5c3ef3766f55475558c97aa04b10908040eb7))
* **memory:** vectorize large corpus publication ([b30c7a7](https://github.com/chio-labs/strata/commit/b30c7a7eac6090a8e6753775d9fb78d2b3929358))


### Documentation

* **memory:** announce repository workflows ([4614502](https://github.com/chio-labs/strata/commit/4614502e97405f3f13f896cf16254608def7d548))

## [0.19.0](https://github.com/chio-labs/strata/compare/v0.18.1...v0.19.0) (2026-07-17)


### Features

* **layers:** enforce main entry visibility ([989dd6e](https://github.com/chio-labs/strata/commit/989dd6edef8c93a067ab25e31097b3e624c84519))
* **layers:** enforce main entry visibility ([3438dce](https://github.com/chio-labs/strata/commit/3438dced68673d9836bf07a7e11cd6291f97b977))

## [0.18.1](https://github.com/chio-labs/strata/compare/v0.18.0...v0.18.1) (2026-07-17)


### Bug Fixes

* **analysis:** remove duplicate Python fact backend ([c4acc84](https://github.com/chio-labs/strata/commit/c4acc84afeae75df9c922edc5b25ead0faa0adfe))
* **analysis:** remove duplicate Python fact backend ([912c712](https://github.com/chio-labs/strata/commit/912c712784fa9ced16118fdd8bca586370a85490))

## [0.18.0](https://github.com/chio-labs/strata/compare/v0.17.0...v0.18.0) (2026-07-17)


### Features

* **analysis:** add native rule-authoring facts ([6930e4c](https://github.com/chio-labs/strata/commit/6930e4cf289fb3e311699b0f3cff07d0d21e8b79))
* **analysis:** add native rule-authoring facts ([116dfb2](https://github.com/chio-labs/strata/commit/116dfb2480522305daa84056dbb7a282840a55e0))


### Performance Improvements

* accelerate repository replay and startup ([2dfe3f9](https://github.com/chio-labs/strata/commit/2dfe3f9dd38a5395819f1b033d09b595f4a00d3c))
* add public execution owners and shared SFT issue discovery ([038daf3](https://github.com/chio-labs/strata/commit/038daf3ac766939d8cc79c5a199b97f794e9338b))
* **cache:** bound high-churn publication ([26692f2](https://github.com/chio-labs/strata/commit/26692f2529e1fca14ad59e37c5c454543afca571))
* **cache:** replay one-edit runs from a sparse collection aggregate ([abca86e](https://github.com/chio-labs/strata/commit/abca86e725b0cb2af34d6db7b8b2d2e2c9d330e7))
* **cache:** reuse implementation path scan ([9076cdd](https://github.com/chio-labs/strata/commit/9076cdd94c46faad48fe3c72d4f054615c580181))
* **cache:** validate warm manifest once ([48f6b64](https://github.com/chio-labs/strata/commit/48f6b6420facdce5ee6756c6d6c5c2ae8dbd6742))
* default full evaluations to automatic worker parallelism ([6037bad](https://github.com/chio-labs/strata/commit/6037bad761353a1530b7201fa80667f3048fd17a))
* establish shared performance foundation ([6b29450](https://github.com/chio-labs/strata/commit/6b294506795cb8911dfd10a089bf65eb43810f1b))
* evaluate no-cache checks across parallel worker partitions ([bbc7354](https://github.com/chio-labs/strata/commit/bbc73547509e5a366618023d746c21a6bc9061a8))
* extract native fact rows in parallel prewarm batches ([6dd3db3](https://github.com/chio-labs/strata/commit/6dd3db3c95dcc52220fad3174fc1ad58af1b816e))
* **instrumentation:** attribute repository query costs ([a1cfcd3](https://github.com/chio-labs/strata/commit/a1cfcd328fe26f31dc674f577f15969a03d7e1a2))

## [0.17.0](https://github.com/chio-labs/strata/compare/v0.16.0...v0.17.0) (2026-07-15)


### Features

* **cli:** prioritize actionable check output ([d85924f](https://github.com/chio-labs/strata/commit/d85924f6b095dee8a9e7fe8e98ddf9b96f685bf2))
* **cli:** prioritize actionable check output ([79167f5](https://github.com/chio-labs/strata/commit/79167f5bb3bcafd752ecead5d2060fae5377e11d))

## [0.16.0](https://github.com/chio-labs/strata/compare/v0.15.3...v0.16.0) (2026-07-15)


### Features

* **roles:** enforce leaf and helper ownership ([42775b5](https://github.com/chio-labs/strata/commit/42775b51d4aa916cb671511acda903c17033e0c2))


### Bug Fixes

* **reporting:** render repository paths with posix separators on every platform ([31ca3b7](https://github.com/chio-labs/strata/commit/31ca3b78ca181dcbae816335da39496c79bc6c93))
* **scaffolding:** make descriptor io, rollback, and map selectors windows-safe ([ca4cae8](https://github.com/chio-labs/strata/commit/ca4cae82ad68485e82465a6c8ccb3e1b81d9b929))
* **scaffolding:** refuse symlinks and directories portably when capturing files ([1aa051e](https://github.com/chio-labs/strata/commit/1aa051e808ffccf55ecfd8dbf5f990d98a338603))
* **windows:** make output and config publication portable ([240b261](https://github.com/chio-labs/strata/commit/240b261164a57f8dad8df9015c28e2a492538e0f))
* **windows:** normalize paths and portable test contracts ([bafad7a](https://github.com/chio-labs/strata/commit/bafad7a6858e69da047d595ef4e1a734c07585b9))


### Performance Improvements

* **config:** compile path patterns once instead of per match ([c11d227](https://github.com/chio-labs/strata/commit/c11d2276817957713ec95524edb9c1632e76c81b))


### Documentation

* **rules:** standardize the custom rule package path ([6b9edf3](https://github.com/chio-labs/strata/commit/6b9edf3bc7ae189e7bdd2342cd75e8389a35d457))

## [0.15.3](https://github.com/chio-labs/strata/compare/v0.15.2...v0.15.3) (2026-07-14)


### Performance Improvements

* **evaluation:** match rule exceptions once per file instead of per rule ([ad000e3](https://github.com/chio-labs/strata/commit/ad000e3d71a8970ede6370385550e9ef1c8bed25))

## [0.15.2](https://github.com/chio-labs/strata/compare/v0.15.1...v0.15.2) (2026-07-14)


### Bug Fixes

* **scaffolding:** guard O_NONBLOCK for platforms without it ([ff41bcd](https://github.com/chio-labs/strata/commit/ff41bcdfae035b5ea51842c45b2c166153d35124))
* **scaffolding:** guard O_NONBLOCK for platforms without it ([894696c](https://github.com/chio-labs/strata/commit/894696c4e6ceb542608f6f5caaa2be6f7787a003))

## [0.15.1](https://github.com/chio-labs/strata/compare/v0.15.0...v0.15.1) (2026-07-14)


### Bug Fixes

* **docs:** document wheel platforms and the rust toolchain requirement ([7257bf4](https://github.com/chio-labs/strata/commit/7257bf4a6d9094b2dfc416ffc08f4115ceb8b652))
* **docs:** document wheel platforms and the rust toolchain requirement ([c6edc0a](https://github.com/chio-labs/strata/commit/c6edc0a21c78e0ada5983c8b87fdd3b2209f1c34))

## [0.15.0](https://github.com/chio-labs/strata/compare/v0.14.0...v0.15.0) (2026-07-14)


### Features

* **analysis:** add native fact backend scaffolding with pass-through delegation ([5b4a9f4](https://github.com/chio-labs/strata/commit/5b4a9f4fd2a8dd12e3ce56a1ffcc1c291c57c4b5))
* **discovery:** add native repository snapshot with canonical path and hash table ([4e0377b](https://github.com/chio-labs/strata/commit/4e0377babbb39857aa538c83475d53f508b76f74))
* **evaluation:** make CPython AST lazy and prewarm native parses in parallel ([db72898](https://github.com/chio-labs/strata/commit/db728981959f0b3b1c82d80cdabe6716d8a85234))
* **facts:** add strict native parser with CPython validity agreement ([06c0361](https://github.com/chio-labs/strata/commit/06c03612c2338999f6a1e9a2045cfdf63d840474))
* **facts:** port harness fact families and close native parity ([8eaf1e0](https://github.com/chio-labs/strata/commit/8eaf1e0e93bccb017cc99e51ead588c862448aaa))
* **facts:** port seventeen fact families to the native backend ([3be79ff](https://github.com/chio-labs/strata/commit/3be79ff1c7c5a64d4fd56f6d3055c1c2841ee4f6))
* **tooling:** add Rust workspace structure checker ([b3b4f45](https://github.com/chio-labs/strata/commit/b3b4f459eb2073961432658dfc26a6df175659a5))
* **tooling:** enforce native-backend performance budgets ([a5c4f58](https://github.com/chio-labs/strata/commit/a5c4f587e268a1ce9fd72e9dbc8deefce29aaf68))
* **tooling:** harden Rust structure checks ([23edb8a](https://github.com/chio-labs/strata/commit/23edb8ac7dbe5cac2111c75296bd15e9ab1eeebe))
* **tooling:** tighten native budget ceilings to measured CI reality ([0e5464a](https://github.com/chio-labs/strata/commit/0e5464a3809256d5b09a55fd707b97149fa3b98f))


### Bug Fixes

* **cache:** accept one concurrent publisher ([76db4da](https://github.com/chio-labs/strata/commit/76db4da06e966493dc72d315934db24104d78124))
* **tests:** import the native extension lazily in parity helpers ([f3fa12f](https://github.com/chio-labs/strata/commit/f3fa12f1dda84443ef4b9c0aae3ad9f79045adb6))
* **tests:** skip native delegation coverage without the extension ([7def24f](https://github.com/chio-labs/strata/commit/7def24fd6b311984e03545ea9156f65163b6c8a9))


### Performance Improvements

* **cache:** encode and validate each publication record once ([ad6420a](https://github.com/chio-labs/strata/commit/ad6420a7ce8a11bb7feabb2e19f976995fe19789))
* **evaluation:** cut path churn and duplicate probe work on the uncached floor ([cf98316](https://github.com/chio-labs/strata/commit/cf983169e8ac26514967f9c1c282a600e66aabe0))
* **evaluation:** remove repeated path, threshold, render, and encode work on hot check paths ([9fa37ae](https://github.com/chio-labs/strata/commit/9fa37aea719c00f38aeb8bdbf5022b8adf700713))

## [0.14.0](https://github.com/chio-labs/strata/compare/v0.13.0...v0.14.0) (2026-07-14)


### Features

* **mapping:** resolve unique nominal protocol dispatch ([c519a28](https://github.com/chio-labs/strata/commit/c519a289b7af457011deb145661f671900fb97e6))
* **mapping:** resolve unique nominal protocol dispatch ([2f1c5c2](https://github.com/chio-labs/strata/commit/2f1c5c2909e450330c2b14627efaa720b5dd0808))

## [0.13.0](https://github.com/chio-labs/strata/compare/v0.12.0...v0.13.0) (2026-07-14)


### Features

* **cli:** flatten skills command and method selectors ([7de134c](https://github.com/chio-labs/strata/commit/7de134c913eed73315e45de5347e98995a3036af))
* **cli:** flatten skills command and method selectors ([9bd6942](https://github.com/chio-labs/strata/commit/9bd6942553984fda1dcdd4f59662e29155802fb5))

## [0.12.0](https://github.com/chio-labs/strata/compare/v0.11.0...v0.12.0) (2026-07-14)


### Features

* **cache:** scope caching per rule with declared cacheability ([800d57c](https://github.com/chio-labs/strata/commit/800d57c2ff1bac56523a622d67a78b37eb213334))
* **cache:** scope caching per rule with declared cacheability ([5e3dde5](https://github.com/chio-labs/strata/commit/5e3dde5a0aadcb9fde7a87c00981b026cdc7bdec))

## [0.11.0](https://github.com/chio-labs/strata/compare/v0.10.1...v0.11.0) (2026-07-14)


### Features

* **instrumentation:** add operation counters with corpus-backed invariants ([a10b1b8](https://github.com/chio-labs/strata/commit/a10b1b85a3cfda473a74921b81fb81597ad790ef))
* **tooling:** add deterministic performance corpus generator ([b3e2a79](https://github.com/chio-labs/strata/commit/b3e2a7916c6bd044e4426bad8a032f204a780fdd))
* **tooling:** add fault-dense budget scenarios ([296edd9](https://github.com/chio-labs/strata/commit/296edd95dcea6a824eb02ce39639c1f1d2eb0438))
* **tooling:** enforce wall-clock performance budgets in CI ([c431cf2](https://github.com/chio-labs/strata/commit/c431cf2c898738fea652a1d2ce91e26c1a0524b2))


### Performance Improvements

* **cache:** replay aggregated observations to skip record decode on warm runs ([816f35f](https://github.com/chio-labs/strata/commit/816f35f134068d77c57574e016ca002d9268f55b))
* **cache:** short-circuit unchanged warm checks with stored output ([ef51060](https://github.com/chio-labs/strata/commit/ef510601e9a4c4cbdc733309a46900b4dd027392))
* **cache:** verify records by stored-bytes identity instead of re-encoding ([f5ee5a1](https://github.com/chio-labs/strata/commit/f5ee5a146f3e1706d2a15ac4381c85ffcabd6555))
* **reporting:** read excerpted sources once per file, not per fault ([7ae1614](https://github.com/chio-labs/strata/commit/7ae16148dd854419ae954ff1039f0874d7a762c6))

## [0.10.1](https://github.com/chio-labs/strata/compare/v0.10.0...v0.10.1) (2026-07-14)


### Performance Improvements

* **cache:** remove quadratic dependency scans and pathlib churn ([1e34299](https://github.com/chio-labs/strata/commit/1e34299f4fcf527da8a63ec3dee98798948ee13e))
* **cache:** remove quadratic dependency scans and pathlib churn ([aa6ac50](https://github.com/chio-labs/strata/commit/aa6ac50e6819a8a5d2a9f489e6dbee81c7e8f408))

## [0.10.0](https://github.com/chio-labs/strata/compare/v0.9.0...v0.10.0) (2026-07-13)


### Features

* **roles:** detect shared domain prefixes ([00bf747](https://github.com/chio-labs/strata/commit/00bf747e0bc1a499e93307e7d4bca391696c3522))
* **rules:** enforce custom rule test coverage ([4cd72b3](https://github.com/chio-labs/strata/commit/4cd72b3960a8b6621857699426eb855e12cbe818))
* **workflow:** add agent-guided policy foundations ([94303bc](https://github.com/chio-labs/strata/commit/94303bc7550996d30061ad2b2886c58970b56275))
* **workflow:** add project-aware skills and rule harness ([21cc7c4](https://github.com/chio-labs/strata/commit/21cc7c4ec4e2e473dc721b1cd5192ddb19685a9d))

## [0.9.0](https://github.com/chio-labs/strata/compare/v0.8.0...v0.9.0) (2026-07-13)


### Features

* **exceptions:** support file-level rule exceptions ([2419d00](https://github.com/chio-labs/strata/commit/2419d002a76974f80720cbb1859725a2281f665b))
* **exceptions:** support file-level rule exceptions ([73df930](https://github.com/chio-labs/strata/commit/73df93059c278ea48038183fbf25bc4861b831da))
* **init:** enforce the default posture ([108a9d5](https://github.com/chio-labs/strata/commit/108a9d506d75f4bd9c76f708d6ef00253e63ddca))
* **init:** enforce the default posture ([775bd22](https://github.com/chio-labs/strata/commit/775bd2246aecd2d39d848c4aa648e6076bd40b96))

## [0.8.0](https://github.com/chio-labs/strata/compare/v0.7.0...v0.8.0) (2026-07-12)


### Features

* **evaluation:** add include and exclude paths ([465fee7](https://github.com/chio-labs/strata/commit/465fee7f5fe4961b9b24bed4cfde9703de8d7317))
* **evaluation:** add include and exclude paths ([ae95857](https://github.com/chio-labs/strata/commit/ae95857e9708fe5585fb31f471d88d388d0bae52))

## [0.7.0](https://github.com/chio-labs/strata/compare/v0.6.0...v0.7.0) (2026-07-12)


### Features

* **rules:** expand naming and local annotation contracts ([9088012](https://github.com/chio-labs/strata/commit/90880124ee679304a03402bbfc0234f381cdaaec))
* **rules:** expand naming and local annotation contracts ([9d9184f](https://github.com/chio-labs/strata/commit/9d9184feaaa95f5c8d515414c6c8fb939a6b72fd))
* **rules:** expose public analysis zones ([7a8d15a](https://github.com/chio-labs/strata/commit/7a8d15a9deeea772236783d2724add08fe6c4171))
* **rules:** expose public analysis zones ([57c12d0](https://github.com/chio-labs/strata/commit/57c12d040b158bef3fa1182bbfaf09717fe51697))

## [0.6.0](https://github.com/chio-labs/strata/compare/v0.5.0...v0.6.0) (2026-07-12)


### Features

* **taxonomy:** settle pre-release rule contracts ([bbb24f7](https://github.com/chio-labs/strata/commit/bbb24f79e28ba2536f9a608ad3e9de8ff74e20dc))
* **taxonomy:** settle pre-release rule contracts ([5f39ad8](https://github.com/chio-labs/strata/commit/5f39ad8eb167c9579dd441889dbdd57e91feeca9))


### Bug Fixes

* **layers:** infer structural import ownership ([733c4cb](https://github.com/chio-labs/strata/commit/733c4cb1dad85c2c425b7320700f4fd366ccbd0f))
* **layers:** infer structural import ownership ([0fde46a](https://github.com/chio-labs/strata/commit/0fde46a81dfd2d78bc4c1a890c8b03c4a4dbf998))
* **taxonomy:** close container and override gaps ([0fb18d8](https://github.com/chio-labs/strata/commit/0fb18d87d0112da1c67bbae5fdc64bcbbbd61de2))
* **taxonomy:** close container and override gaps ([7da5d4e](https://github.com/chio-labs/strata/commit/7da5d4e38cfe32be29c02cbc5a7ccdbceac1c212))


### Performance Improvements

* **map:** cache project declaration indexes ([4d58c75](https://github.com/chio-labs/strata/commit/4d58c75ba376992260291485c53ba3827d5d8b26))
* **map:** cache project declaration indexes ([cb72ac1](https://github.com/chio-labs/strata/commit/cb72ac143754798ed6fba3207882529893d50d71))

## [0.5.0](https://github.com/chio-labs/strata/compare/v0.4.0...v0.5.0) (2026-07-12)


### Features

* **init:** add guided project setup ([77d1d72](https://github.com/chio-labs/strata/commit/77d1d7252f1a62318f28458e6889027e436a439c))
* **init:** make setup idempotent and cache-clean ([2c1fa25](https://github.com/chio-labs/strata/commit/2c1fa25a5c7303b127b49bc5fbd5b029b8e0b299))
* **roles:** enforce leaf-or-branch domains ([539169e](https://github.com/chio-labs/strata/commit/539169e129684971d557666057a1d362ba0f1eeb))

## [0.4.0](https://github.com/chio-labs/strata/compare/v0.3.0...v0.4.0) (2026-07-12)


### Features

* **map:** resolve concrete method calls ([333b1da](https://github.com/chio-labs/strata/commit/333b1da71f75fac3713bcc90fb64d187417db3a8))
* **map:** resolve concrete method calls ([d3d96ff](https://github.com/chio-labs/strata/commit/d3d96ff7c553bef0bdddc71ec2a92b0d1cedec76))


### Bug Fixes

* **shape:** enforce keyword-only threshold placement ([edaa69a](https://github.com/chio-labs/strata/commit/edaa69a32f45639e34f61a50a48c34124912157a))

## [0.3.0](https://github.com/chio-labs/strata/compare/v0.2.0...v0.3.0) (2026-07-12)


### Features

* **analysis:** share dependency query observation ([3a18341](https://github.com/chio-labs/strata/commit/3a183418252095281934c18c836d6a20c396cb0e))
* **cache:** add atomic record storage ([76dc8ae](https://github.com/chio-labs/strata/commit/76dc8aef604b6ec097d4187309ff2d6953ed1ad8))
* **cache:** add fingerprint foundation ([040b9f8](https://github.com/chio-labs/strata/commit/040b9f852898fbe429da30c99aef839cf6e3d0da))
* **cache:** add indexed result repository ([ce2ac82](https://github.com/chio-labs/strata/commit/ce2ac82c0663b48c7e0b2e7c6ed975e1a8bc2a8c))
* **cache:** add typed result records ([1819841](https://github.com/chio-labs/strata/commit/181984166af6f4758ca07e95965ad11895fc3fac))
* **cache:** capture file evaluation inputs ([fde9143](https://github.com/chio-labs/strata/commit/fde9143259aa0183c28e919dd286e1c368612429))
* **cache:** enable persistent checks by default ([35e52d1](https://github.com/chio-labs/strata/commit/35e52d18d907b1d8c57dd15bfbd6a42ebca43b37))
* **cache:** expose transactional persistent checks ([bd89f7d](https://github.com/chio-labs/strata/commit/bd89f7d6b59783a6eb6edea73439c23a03014b82))
* **cache:** reuse dependency-aware file results ([74b2a86](https://github.com/chio-labs/strata/commit/74b2a868c25f2595e3f99df534a603dc8f453eb0))
* **cache:** sweep generations and degrade publication failures ([115d9e5](https://github.com/chio-labs/strata/commit/115d9e520346cf03e9f1908818c4dd43e98b47f6))
* **cache:** verify custom rules under a require-cacheable policy ([850928e](https://github.com/chio-labs/strata/commit/850928e32cdbaf07c7b5dc2650d8203f12b0e683))
* **rules:** enforce hermetic rule execution ([0e2dedf](https://github.com/chio-labs/strata/commit/0e2dedf98e7c6fed04bc626bc1f454a5e6e5ccc5))
* **rules:** organize test rule codes by concern ([def7a2b](https://github.com/chio-labs/strata/commit/def7a2bf2ba4ca3c1c2e4675342f188534a2843b))


### Bug Fixes

* **config:** honor configured project layouts ([44cf549](https://github.com/chio-labs/strata/commit/44cf549cae693905f4bc43e969baf7b89c3b5ba5))

## [0.2.0](https://github.com/chio-labs/strata/compare/v0.1.2...v0.2.0) (2026-07-11)


### Features

* **agentdocs:** strengthen Strata workflow guidance ([bec95ac](https://github.com/chio-labs/strata/commit/bec95ac87c1ae230f0b73bf2ec2371ed7fb05e01))
* **analysis:** add module declaration facts ([ef08734](https://github.com/chio-labs/strata/commit/ef08734104b1f93aed7c5b41e6d599af63298a69))
* **analysis:** add parameter mutation facts ([754e210](https://github.com/chio-labs/strata/commit/754e210b66702350920bf72404361904dde63c73))
* **analysis:** add shared dataclass facts ([5f6ec9a](https://github.com/chio-labs/strata/commit/5f6ec9a09d78febf665a3f9fc325c9334af961bf))
* **analysis:** add shared pytest metadata ([be656be](https://github.com/chio-labs/strata/commit/be656bedb633fc1cca2f8b3c7f06719a39ba2c9f))
* **analysis:** complete annotation and comprehension facts ([0333322](https://github.com/chio-labs/strata/commit/033332257aa8b52710067dea13116b38395ccfff))
* **analysis:** complete backend-neutral core cutover ([041404d](https://github.com/chio-labs/strata/commit/041404d4afc4b13625dffe7fe4b866f386a13fa4))
* **analysis:** expand module declaration facts ([934be48](https://github.com/chio-labs/strata/commit/934be48b112397637a5ee412addae34bef31c03c))
* **analysis:** expand shared core facts ([5dd77ea](https://github.com/chio-labs/strata/commit/5dd77ea45ef924ad9979e0c230c0666b1c767731))
* **analysis:** track filesystem dependencies ([32976f9](https://github.com/chio-labs/strata/commit/32976f922ede391ecd40595ffb458252ca703fc8))
* **config:** add symbol-scoped rule exceptions ([3fcc994](https://github.com/chio-labs/strata/commit/3fcc994aae94c5d5d24d685ada182c8533ead2ae))
* **config:** add symbol-scoped rule exceptions ([dd4cb24](https://github.com/chio-labs/strata/commit/dd4cb2416d382cbd73b200270da285a2d01ff67f))
* **evaluation:** add shared analysis foundation ([19a5aa1](https://github.com/chio-labs/strata/commit/19a5aa1e9895818f4722eb4314434f6e44ae858d))
* **evaluation:** return project dependencies ([ea9b33b](https://github.com/chio-labs/strata/commit/ea9b33b16b64df124f5ad0cc25524cc8bfc6a6e5))


### Performance Improvements

* **analysis:** narrow semantic fact traversal ([32dc1c7](https://github.com/chio-labs/strata/commit/32dc1c7b91a7bdd8354dae290ce2a9f40571f8a1))
* **analysis:** reduce repeated fact traversal ([dfb142a](https://github.com/chio-labs/strata/commit/dfb142a7f29a65236b7cd4c9944d8cd749f26bf4))
* **analysis:** retain test type facts only ([cee2e7c](https://github.com/chio-labs/strata/commit/cee2e7c66653331d085c99159395f436b7a31345))

## [0.1.2](https://github.com/chio-labs/strata/compare/v0.1.1...v0.1.2) (2026-07-10)


### Documentation

* remove development footer ([53c07b8](https://github.com/chio-labs/strata/commit/53c07b8bf5eedd1d1e5b266c7263804a3a660e9c))
* show strata map call tree ([96f77f2](https://github.com/chio-labs/strata/commit/96f77f23290bafe226965f87b803707fb1bc911a))

## [0.1.1](https://github.com/chio-labs/strata/compare/v0.1.0...v0.1.1) (2026-07-10)


### Documentation

* align package tagline ([7d2ad5e](https://github.com/chio-labs/strata/commit/7d2ad5e0a7546d10f8519977fb15386c6b8c2df3))
* align package tagline ([fbf65d9](https://github.com/chio-labs/strata/commit/fbf65d99115872adbba3c230b70dce18b93ca7da))
* improve package presentation ([7f63abe](https://github.com/chio-labs/strata/commit/7f63abe35d3044b5d6ff5bf280d51a0badd0ada3))
* improve package presentation ([a644413](https://github.com/chio-labs/strata/commit/a644413936476636f4bd4f0b8c29aef919494a60))

## [0.1.0](https://github.com/chio-labs/strata/compare/v0.0.2...v0.1.0) (2026-07-10)


### Features

* **agentdocs:** guide navigation and work handoffs ([a55305d](https://github.com/chio-labs/strata/commit/a55305d3bece7a1f78dcbc299f348cdaed0f6dc4))
* **agentdocs:** tailor skills to active rules ([654ae11](https://github.com/chio-labs/strata/commit/654ae118f8733f07b8b528a6ae4a60fea287915d))
* **api:** add public contract and vocabulary ([6f493d6](https://github.com/chio-labs/strata/commit/6f493d61bf11604d22112c3b39ff8417b27edb77))
* **checkers:** add generic package naming rule ([fa45dc2](https://github.com/chio-labs/strata/commit/fa45dc2e3b6ef20a98006f63cb44ca32fcdadff5))
* **checkers:** add keyword-only parameter rule ([2628559](https://github.com/chio-labs/strata/commit/26285595b4eafb7ddd67e773bc6e34d95e02d032))
* **cli:** add repository-aware skills update ([af83175](https://github.com/chio-labs/strata/commit/af83175c2e264629835520d311f747622827bdc4))
* **cli:** add rule skill and map commands ([285fd20](https://github.com/chio-labs/strata/commit/285fd20fd262794a906b827c2ea65479106b50ea))
* **cli:** add ruleset loading and check command ([50df774](https://github.com/chio-labs/strata/commit/50df774aec954f559ffc0728fc497bbbf35517b7))
* **cli:** refine map styling and skills workflow ([b01cc80](https://github.com/chio-labs/strata/commit/b01cc80857e74324dad0a95b6062a50528d0f10d))
* **cli:** refine terminal presentation ([1849f81](https://github.com/chio-labs/strata/commit/1849f81bf430fc0c46fec73e3ea8c5c40b08a19b))
* complete self-hosting cutover ([ea575f4](https://github.com/chio-labs/strata/commit/ea575f442e0524fe0c2440089af21da35b7d21c8))
* **config:** add configuration loading ([9e7946a](https://github.com/chio-labs/strata/commit/9e7946acf5aa23c90149718a6954134817032e87))
* **discovery:** add config-driven discovery ([25b7d89](https://github.com/chio-labs/strata/commit/25b7d89d0333744b0ea162943a04f11216b782ee))
* enable strata self-hosting ([e41e221](https://github.com/chio-labs/strata/commit/e41e2219048fbaa34b3005377c7d6a8ac078d7dd))
* **evaluation:** add engine and rule context ([9e366f4](https://github.com/chio-labs/strata/commit/9e366f4edb53ff2a0cf27836734aeef4b6efafa6))
* expand mapping and diagnostics ([5f30d71](https://github.com/chio-labs/strata/commit/5f30d71d944c96f014b4a406bab9eb580770acfa))
* **rules:** add annotations family ([8faf963](https://github.com/chio-labs/strata/commit/8faf96300966791119708decbf0f7b5628add74d))
* **rules:** add hygiene family ([c65e37b](https://github.com/chio-labs/strata/commit/c65e37b3821edf41fe7a4df4c9013b419489314b))
* **rules:** add layers family ([70fb57e](https://github.com/chio-labs/strata/commit/70fb57e614f4cae15ad4e65b2ed1dc5eddbbfe87))
* **rules:** add naming contract rules ([69cd135](https://github.com/chio-labs/strata/commit/69cd135e0b10707b508eb8fe53aaec004340b623))
* **rules:** add role layout rules ([47c4b03](https://github.com/chio-labs/strata/commit/47c4b033a2cd5b0cf64eb30fdda527d390a73d9d))
* **rules:** add role ownership rules ([a495285](https://github.com/chio-labs/strata/commit/a495285bbd03fe5b7a90f201984dcca77a4c5c2e))
* **rules:** add role surface and shape rules ([eeb9a6d](https://github.com/chio-labs/strata/commit/eeb9a6dfd1d92c206298f6834ebdda7dfd74957c))
* **rules:** add shape family ([92d2b53](https://github.com/chio-labs/strata/commit/92d2b5302303ee02e7424a6b15319b1c3c70f72d))
* **rules:** add tests family ([84a941b](https://github.com/chio-labs/strata/commit/84a941b61db9ebbf9495b01c567107305405bef7))
* **rules:** enable decision literal checks ([573ddfb](https://github.com/chio-labs/strata/commit/573ddfb9dea60058458ef08ca698fb7c6ad482ed))
* **rules:** enforce domain package names ([bff9a51](https://github.com/chio-labs/strata/commit/bff9a51d82bd2024ab9275cff10091cfe58bd002))
* **rules:** enforce readable control flow ([3115db5](https://github.com/chio-labs/strata/commit/3115db5f0a2bf7b5f378c7762a809fa5b16594dc))
* **rules:** enforce tooling structure and decision literals ([6609207](https://github.com/chio-labs/strata/commit/66092072cd408065da723c485f427635c01e961e))


### Bug Fixes

* **checkers:** allow TYPE_CHECKING import blocks ([6eab87e](https://github.com/chio-labs/strata/commit/6eab87ee5ae3ee8591b79a8583beebdcfe8628b3))
* **checkers:** enforce domain role placement ([3a0a2ec](https://github.com/chio-labs/strata/commit/3a0a2ec785a1f6578ed6d2f32eb138f2baeeb82f))
* **rules:** type custom family selector ([8995f84](https://github.com/chio-labs/strata/commit/8995f840eb8305670cc0324d3dd76f1366e1396a))


### Performance Improvements

* reduce repeated analysis work ([61f769f](https://github.com/chio-labs/strata/commit/61f769ff60b896341ffa716c076c4153125e5be1))


### Documentation

* streamline project readme ([21c0c36](https://github.com/chio-labs/strata/commit/21c0c3601533bf27dbb0dd13db35ad0fa5f4c207))
* streamline project readme ([c09c8a3](https://github.com/chio-labs/strata/commit/c09c8a3e5f1150c774e5d7f460348364216f82dc))

## Changelog

Release notes are managed by release-please.
