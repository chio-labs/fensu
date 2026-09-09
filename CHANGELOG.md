# Changelog

## [0.14.3](https://github.com/chio-labs/fensu/compare/v0.14.2...v0.14.3) (2026-09-09)


### Bug Fixes

* refresh lock metadata before crate publish ([#69](https://github.com/chio-labs/fensu/issues/69)) ([9466159](https://github.com/chio-labs/fensu/commit/946615913cb9595be653b63c37e6abd84b7d12a7))

## [0.14.2](https://github.com/chio-labs/fensu/compare/v0.14.1...v0.14.2) (2026-09-09)


### Bug Fixes

* refresh release lockfile ([#67](https://github.com/chio-labs/fensu/issues/67)) ([5adf414](https://github.com/chio-labs/fensu/commit/5adf414b671dd2b8393fc0eeb5de5196b05a1ed3))

## [0.14.1](https://github.com/chio-labs/fensu/compare/v0.14.0...v0.14.1) (2026-09-09)


### Bug Fixes

* refresh public fixtures ([1725f64](https://github.com/chio-labs/fensu/commit/1725f64f47d62ce609eaa090458fe8b040a90b1e))

## [0.14.0](https://github.com/chio-labs/fensu/compare/v0.13.1...v0.14.0) (2026-08-27)


### Features

* detect role laundering through re-exports ([#64](https://github.com/chio-labs/fensu/issues/64)) ([c06b254](https://github.com/chio-labs/fensu/commit/c06b2541dc9a4ed67d76062f14579e9741b37f9a))

## [0.13.1](https://github.com/chio-labs/fensu/compare/v0.13.0...v0.13.1) (2026-08-24)


### Bug Fixes

* **release:** use delivery app for release PRs ([#61](https://github.com/chio-labs/fensu/issues/61)) ([79be68b](https://github.com/chio-labs/fensu/commit/79be68b03cd70d3ef8da23a53f3a82dc26f5236a))

## [0.13.0](https://github.com/chio-labs/fensu/compare/v0.12.0...v0.13.0) (2026-08-22)


### Features

* harden shared lifecycle and structure contracts ([#55](https://github.com/chio-labs/fensu/issues/55)) ([f027fe3](https://github.com/chio-labs/fensu/commit/f027fe3fcad98ea398c0c9a88a3522e6635b1cb1))


### Bug Fixes

* bridge trusted release statuses ([#58](https://github.com/chio-labs/fensu/issues/58)) ([0e45b9c](https://github.com/chio-labs/fensu/commit/0e45b9cf3788cb1c59bea52abc1db6d4718d38a5))
* stabilize release head validation ([#57](https://github.com/chio-labs/fensu/issues/57)) ([59b484d](https://github.com/chio-labs/fensu/commit/59b484d9ff57c41807d7e7559b3b7b3ec3fd6b69))

## [0.12.0](https://github.com/chio-labs/fensu/compare/v0.11.0...v0.12.0) (2026-08-22)


### Features

* extract reusable policy runtime ([#51](https://github.com/chio-labs/fensu/issues/51)) ([196d2f1](https://github.com/chio-labs/fensu/commit/196d2f1926b6d7123333d9f981a02c6cc52ebb74))


### Bug Fixes

* preserve release verification after branch deletion ([#53](https://github.com/chio-labs/fensu/issues/53)) ([fd73ae6](https://github.com/chio-labs/fensu/commit/fd73ae6bbf737a38a35691701b3962e1fbcd294c))
* target repository for release checks ([#54](https://github.com/chio-labs/fensu/issues/54)) ([00c8ad4](https://github.com/chio-labs/fensu/commit/00c8ad46b134e43a2c6de6ebfb55ea5a3e4f2a9b))

## [0.11.0](https://github.com/chio-labs/fensu/compare/v0.10.0...v0.11.0) (2026-08-11)


### Features

* add native TypeScript and SvelteKit rule packs ([0f8e972](https://github.com/chio-labs/fensu/commit/0f8e972589ec8bc385db7f55775064e194e524cd))
* add native TypeScript and SvelteKit rule packs ([d8b2188](https://github.com/chio-labs/fensu/commit/d8b2188bbeaf8386e6e3685a327b22a2ab39e37f))

## [0.10.0](https://github.com/chio-labs/fensu/compare/v0.9.4...v0.10.0) (2026-08-10)


### Features

* add named analyzer targets ([f7b4ca2](https://github.com/chio-labs/fensu/commit/f7b4ca2c8d774846eec6855d5f9100c1fad30cad))
* add native SvelteKit architecture policy ([0450940](https://github.com/chio-labs/fensu/commit/04509402dcb4c9c6b22b6f1a1db983ff3131d965))
* add native TypeScript and Svelte parsers ([65d9633](https://github.com/chio-labs/fensu/commit/65d96334f9b7df5659211eff29812d3389d56a6b))
* add native TypeScript architecture policy ([8c02914](https://github.com/chio-labs/fensu/commit/8c02914c1003132562ba580917b99fac80ef3b0a))
* add SvelteKit target onboarding ([55f86ba](https://github.com/chio-labs/fensu/commit/55f86ba0ed8d9ffad06e88fb9689a01102cd1451))
* add typed analyzer contracts ([d08db9b](https://github.com/chio-labs/fensu/commit/d08db9b0927b9f6c1572c27e08cd6ed7624211ce))
* aggregate checks across analyzer targets ([802c94b](https://github.com/chio-labs/fensu/commit/802c94bf355e354bef92b772567ab500c5f05fbe))
* complete native SvelteKit analyzer support ([9551751](https://github.com/chio-labs/fensu/commit/9551751beb28bb537c589f2faa26dda49300c3e6))
* configure web test layouts ([dac54b2](https://github.com/chio-labs/fensu/commit/dac54b2891b401a1ee2b9329a15f9e4bf84943fb))
* preserve web threshold compatibility ([ff92bbc](https://github.com/chio-labs/fensu/commit/ff92bbc02dc77e3e25791a528d9ca5392e0318b8))
* support nested analyzer target roots ([3bf2c87](https://github.com/chio-labs/fensu/commit/3bf2c87c10acdee61f74f745aaeade79cbacf6d8))
* wire native frontend analyzer execution ([d2640e3](https://github.com/chio-labs/fensu/commit/d2640e3f7ef89399ce955daf39060cc9da08ba94))


### Bug Fixes

* allow empty evaluation exclusions ([951b6b7](https://github.com/chio-labs/fensu/commit/951b6b7b3b890982cb5a94e4f450d1a4bd9decfd))
* normalize cross-platform repository paths ([99e5bce](https://github.com/chio-labs/fensu/commit/99e5bce2c8cc02dc83c753fd1394b6cafa5fd564))
* preserve readonly web test cases ([b10e2d0](https://github.com/chio-labs/fensu/commit/b10e2d0d36714ddad9a8775781487d3867f2697a))
* provision cross-platform test runtimes ([556f899](https://github.com/chio-labs/fensu/commit/556f8990e80df61f3a62239b746bf1eac8d6650b))

## [0.9.4](https://github.com/chio-labs/fensu/compare/v0.9.3...v0.9.4) (2026-08-09)


### Bug Fixes

* restore native Dagster rule parity ([561166f](https://github.com/chio-labs/fensu/commit/561166f16157331adb9406615d181518076278aa))
* restore native Dagster rule parity ([a9dac56](https://github.com/chio-labs/fensu/commit/a9dac56d99515e2f923c60056734128fadbb118e))

## [0.9.3](https://github.com/chio-labs/fensu/compare/v0.9.2...v0.9.3) (2026-08-09)


### Bug Fixes

* execute native rule packs consistently ([d2f65b1](https://github.com/chio-labs/fensu/commit/d2f65b1da8c087791499cf53f225ce9786f889ac))
* execute native rule packs consistently ([3397139](https://github.com/chio-labs/fensu/commit/33971391568b593fdb7eae2d878b09a421bdd7e4))
* reject unmatched rule selectors ([b1ee6b4](https://github.com/chio-labs/fensu/commit/b1ee6b45a491c27b7b23c45b2da0d82255a5f7ac))
* reject unmatched rule selectors ([68c28fb](https://github.com/chio-labs/fensu/commit/68c28fba8b700249daa5094c212ed7cb9eb75dd9))

## [0.9.2](https://github.com/chio-labs/fensu/compare/v0.9.1...v0.9.2) (2026-08-07)


### Bug Fixes

* make dagster rule codes contiguous ([83305c7](https://github.com/chio-labs/fensu/commit/83305c726e1d8cddf1aac88ce087e22b890fb154))
* make dagster rule codes contiguous ([cda05f2](https://github.com/chio-labs/fensu/commit/cda05f219874f5b8d6e646fb6c14e0757aa80714))

## [0.9.1](https://github.com/chio-labs/fensu/compare/v0.9.0...v0.9.1) (2026-08-07)


### Bug Fixes

* align native rules with canonical policy ([f19b81c](https://github.com/chio-labs/fensu/commit/f19b81c55b0a37b8853a90faf5e517d6dc8dd826))
* derive repository guidance from rule policy ([45d255c](https://github.com/chio-labs/fensu/commit/45d255caca16877fa0eb816128ef9f642986d9dd))
* honor configured map roots ([1551d2c](https://github.com/chio-labs/fensu/commit/1551d2c5ecc79c69745a5e174f2ba60731fc8492))
* make catalogue inspection fail closed ([ae82a48](https://github.com/chio-labs/fensu/commit/ae82a48b1b5945cc49b6b24754c0f7646dd241c1))
* make native configuration fail closed ([24bd4ba](https://github.com/chio-labs/fensu/commit/24bd4ba5dac570ad81458da20c8460f7b6e11266))

## [0.9.0](https://github.com/chio-labs/fensu/compare/v0.8.1...v0.9.0) (2026-08-07)


### Features

* add native dagster rule pack ([15cff16](https://github.com/chio-labs/fensu/commit/15cff162781d982d9230fb11f2a317d758206de6))
* add native dagster rule pack ([fae0ac0](https://github.com/chio-labs/fensu/commit/fae0ac06ac281c9130991174b96b5f59de083deb))

## [0.8.1](https://github.com/chio-labs/fensu/compare/v0.8.0...v0.8.1) (2026-07-27)


### Bug Fixes

* make skill ownership relocatable ([55ba0d7](https://github.com/chio-labs/fensu/commit/55ba0d72af6e5cad00be158b4f6ea132c880c9a0))
* make skill ownership relocatable ([b5ca716](https://github.com/chio-labs/fensu/commit/b5ca7168f404487f6529e336d876c64beea8f0dd))

## [0.8.0](https://github.com/chio-labs/fensu/compare/v0.7.0...v0.8.0) (2026-07-26)


### Features

* derive rule surfaces from canonical metadata ([d81e13d](https://github.com/chio-labs/fensu/commit/d81e13d00095477e0c158b0c1efac5c02a1e26b1))
* enforce rust function shape parity ([9942937](https://github.com/chio-labs/fensu/commit/99429374914f11bedc9ebfc885fa078b979034cd))
* enforce rust hygiene and binding clarity ([e7608ff](https://github.com/chio-labs/fensu/commit/e7608ffceea59a76d3400dab052f68b0db9b0e5a))
* enforce rust test conventions ([623f208](https://github.com/chio-labs/fensu/commit/623f208aae57303d67bfbd4072808cf5bf60983b))
* enforce rust tooling role boundaries ([bba862e](https://github.com/chio-labs/fensu/commit/bba862ebda789257281e5c858a78c1931c5e4592))
* enforce rust visibility and entry boundaries ([2013050](https://github.com/chio-labs/fensu/commit/2013050a75f7abd87670e966ee8a6b7b20306f3d))
* enforce transitive helper ownership ([c1fc7df](https://github.com/chio-labs/fensu/commit/c1fc7dfa513a751cbc86e847b8ea88f1df274cb8))
* report domain shape, role boundaries, and missing main entries ([c5cb6d1](https://github.com/chio-labs/fensu/commit/c5cb6d161228420fe8de4dcc88b13a3401644a82))
* report test modules that no harness declares ([33a552d](https://github.com/chio-labs/fensu/commit/33a552dbb543adda93850a004c951a976ba714ef))
* report ungrouped helper prefix families and reserved role names ([3d04780](https://github.com/chio-labs/fensu/commit/3d047809ebc11036a22281d266c24efbdfd57ae9))


### Bug Fixes

* align rule lookup fault color ([54fafa5](https://github.com/chio-labs/fensu/commit/54fafa5f7b02b7e8042f669c88351169c0df2da5))
* stabilize empty mapping test module ([8be98df](https://github.com/chio-labs/fensu/commit/8be98df7266e36039bb1c6c760fb167c0d0fd3c4))

## [0.7.0](https://github.com/chio-labs/fensu/compare/v0.6.0...v0.7.0) (2026-07-26)


### Features

* add --color to check in both implementations ([205a3c2](https://github.com/chio-labs/fensu/commit/205a3c29ea744a3c821b7ea6fce270fee05c972d))
* make the test scope vocabulary configurable ([a2f814f](https://github.com/chio-labs/fensu/commit/a2f814f6dc638d4982810baa3e0c145b280c3d30))
* make the test scope vocabulary configurable ([f01479d](https://github.com/chio-labs/fensu/commit/f01479ded648bdb4857b28b5ebc798bb9e40bf9c))


### Bug Fixes

* honor symbol-scoped rule exceptions in native checks ([50a83b0](https://github.com/chio-labs/fensu/commit/50a83b0c8ba53bbda981922fbe9afeb8c4838261))
* match rule exception paths exactly and skip unevaluated rules ([c30eeb2](https://github.com/chio-labs/fensu/commit/c30eeb272fab68343f2f8e2733232b99c2dc5ce7))
* move the fault color test into a compliant harness ([52ac837](https://github.com/chio-labs/fensu/commit/52ac83736d4913cd37a01f9e7776945241e3e11e))
* restore historical fault output color ([6870aa9](https://github.com/chio-labs/fensu/commit/6870aa90beb6c9e3f77670e176c35c7eb78bfca0))
* restore historical fault output color ([461faf8](https://github.com/chio-labs/fensu/commit/461faf8d68a43d58ec8236267acd1fa3c7e151ea))
* validate rule exception targets during native checks ([cde9488](https://github.com/chio-labs/fensu/commit/cde94884f7e7ad4572f54926f1937cf8315efe43))
* validate rule exception targets during native checks ([79c51d4](https://github.com/chio-labs/fensu/commit/79c51d402b021b5d3707ed047ce8a1fe9d128ea7))

## [0.6.0](https://github.com/chio-labs/fensu/compare/v0.5.2...v0.6.0) (2026-07-26)


### Features

* report implicit namespace packages during init ([d456178](https://github.com/chio-labs/fensu/commit/d45617831bf3ab616f02d8750076d2ad9ec1a295))


### Bug Fixes

* keep init from writing nested detected roots ([ee34db3](https://github.com/chio-labs/fensu/commit/ee34db38d78d600e92aef16fe39ecab2bbe23ad3))

## [0.5.2](https://github.com/chio-labs/fensu/compare/v0.5.1...v0.5.2) (2026-07-25)


### Bug Fixes

* restore the CLI build interpreter and retag only ([fc5857a](https://github.com/chio-labs/fensu/commit/fc5857a9db9bab0f7a4ed74772518d67943b3189))
* restore the CLI build interpreter and retag only ([a741a7e](https://github.com/chio-labs/fensu/commit/a741a7e767561e5deafe42eb9deb3ca4331ab311))

## [0.5.1](https://github.com/chio-labs/fensu/compare/v0.5.0...v0.5.1) (2026-07-25)


### Bug Fixes

* tag native CLI wheels as interpreter-agnostic ([da314c4](https://github.com/chio-labs/fensu/commit/da314c413a9235c445433b5b3225116a3ae5b8a0))
* tag native CLI wheels as interpreter-agnostic ([9b3bfb5](https://github.com/chio-labs/fensu/commit/9b3bfb5eb93eeade7372576a4f8b3e73dcaa4a58))

## [0.5.0](https://github.com/chio-labs/fensu/compare/v0.4.1...v0.5.0) (2026-07-23)


### Features

* add typed per-rule options ([a313a69](https://github.com/chio-labs/fensu/commit/a313a69b436dcd3b98bd9b258fe71a7bdb8a4082))
* add typed per-rule options ([517a952](https://github.com/chio-labs/fensu/commit/517a95263308db9949ad57a4bf3276903de6f04e))

## [0.4.1](https://github.com/chio-labs/fensu/compare/v0.4.0...v0.4.1) (2026-07-23)


### Documentation

* align README onboarding language ([f3c71fc](https://github.com/chio-labs/fensu/commit/f3c71fc50cdbccae99f30e669dbe2b2397098720))
* align README onboarding language ([2534e5d](https://github.com/chio-labs/fensu/commit/2534e5d9fb0d0629c4891f06624cddf60774f781))

## [0.4.0](https://github.com/chio-labs/fensu/compare/v0.3.0...v0.4.0) (2026-07-22)


### Features

* harden check policy and agent onboarding ([0c84d60](https://github.com/chio-labs/fensu/commit/0c84d6071341fa875cb9485ca5a87030fc57adf1))
* harden check policy and agent onboarding ([404b619](https://github.com/chio-labs/fensu/commit/404b619b9efa758f3077fe31b629b533ee15954e))


### Bug Fixes

* release cleanup handles before removal ([79133b7](https://github.com/chio-labs/fensu/commit/79133b7d40b66f1f6d99a24861fe9dd2f638bde4))

## [0.3.0](https://github.com/chio-labs/fensu/compare/v0.2.2...v0.3.0) (2026-07-21)


### Features

* **cli:** run built-in commands natively ([a405bf2](https://github.com/chio-labs/fensu/commit/a405bf29e42efb5c3a5e098b91c4ecbcb27545ad))
* **cli:** run built-in commands natively ([ffc19f7](https://github.com/chio-labs/fensu/commit/ffc19f7e9a7026d2d7ef4cc8c9b38b95c5192474))

## [0.2.2](https://github.com/chio-labs/fensu/compare/v0.2.1...v0.2.2) (2026-07-19)


### Bug Fixes

* allow retrying partial PyPI publishes ([476bce6](https://github.com/chio-labs/fensu/commit/476bce6cc9ddfdf187332081f82835cc0020fcdb))
* allow retrying partial PyPI publishes ([16aa17e](https://github.com/chio-labs/fensu/commit/16aa17e70c5b97351b85327a686003c597e0c538))

## [0.2.1](https://github.com/chio-labs/fensu/compare/v0.2.0...v0.2.1) (2026-07-19)


### Bug Fixes

* select Python 3.12 for CLI wheels ([12272ba](https://github.com/chio-labs/fensu/commit/12272ba29d78b98274624c314927008168c069ce))
* select Python 3.12 for CLI wheels ([246cbeb](https://github.com/chio-labs/fensu/commit/246cbebae93c65725345514eeb6d5be1c01a977b))

## [0.2.0](https://github.com/chio-labs/fensu/compare/v0.1.0...v0.2.0) (2026-07-19)


### Features

* **agentdocs:** guide navigation and work handoffs ([a55305d](https://github.com/chio-labs/fensu/commit/a55305d3bece7a1f78dcbc299f348cdaed0f6dc4))
* **agentdocs:** strengthen Strata workflow guidance ([bec95ac](https://github.com/chio-labs/fensu/commit/bec95ac87c1ae230f0b73bf2ec2371ed7fb05e01))
* **agentdocs:** tailor skills to active rules ([654ae11](https://github.com/chio-labs/fensu/commit/654ae118f8733f07b8b528a6ae4a60fea287915d))
* **analysis:** add module declaration facts ([ef08734](https://github.com/chio-labs/fensu/commit/ef08734104b1f93aed7c5b41e6d599af63298a69))
* **analysis:** add native fact backend scaffolding with pass-through delegation ([5b4a9f4](https://github.com/chio-labs/fensu/commit/5b4a9f4fd2a8dd12e3ce56a1ffcc1c291c57c4b5))
* **analysis:** add native rule-authoring facts ([6930e4c](https://github.com/chio-labs/fensu/commit/6930e4cf289fb3e311699b0f3cff07d0d21e8b79))
* **analysis:** add native rule-authoring facts ([116dfb2](https://github.com/chio-labs/fensu/commit/116dfb2480522305daa84056dbb7a282840a55e0))
* **analysis:** add parameter mutation facts ([754e210](https://github.com/chio-labs/fensu/commit/754e210b66702350920bf72404361904dde63c73))
* **analysis:** add shared dataclass facts ([5f6ec9a](https://github.com/chio-labs/fensu/commit/5f6ec9a09d78febf665a3f9fc325c9334af961bf))
* **analysis:** add shared pytest metadata ([be656be](https://github.com/chio-labs/fensu/commit/be656bedb633fc1cca2f8b3c7f06719a39ba2c9f))
* **analysis:** complete annotation and comprehension facts ([0333322](https://github.com/chio-labs/fensu/commit/033332257aa8b52710067dea13116b38395ccfff))
* **analysis:** complete backend-neutral core cutover ([041404d](https://github.com/chio-labs/fensu/commit/041404d4afc4b13625dffe7fe4b866f386a13fa4))
* **analysis:** expand module declaration facts ([934be48](https://github.com/chio-labs/fensu/commit/934be48b112397637a5ee412addae34bef31c03c))
* **analysis:** expand shared core facts ([5dd77ea](https://github.com/chio-labs/fensu/commit/5dd77ea45ef924ad9979e0c230c0666b1c767731))
* **analysis:** share dependency query observation ([3a18341](https://github.com/chio-labs/fensu/commit/3a183418252095281934c18c836d6a20c396cb0e))
* **analysis:** track filesystem dependencies ([32976f9](https://github.com/chio-labs/fensu/commit/32976f922ede391ecd40595ffb458252ca703fc8))
* **api:** add public contract and vocabulary ([6f493d6](https://github.com/chio-labs/fensu/commit/6f493d61bf11604d22112c3b39ff8417b27edb77))
* **cache:** add atomic record storage ([76dc8ae](https://github.com/chio-labs/fensu/commit/76dc8aef604b6ec097d4187309ff2d6953ed1ad8))
* **cache:** add fingerprint foundation ([040b9f8](https://github.com/chio-labs/fensu/commit/040b9f852898fbe429da30c99aef839cf6e3d0da))
* **cache:** add indexed result repository ([ce2ac82](https://github.com/chio-labs/fensu/commit/ce2ac82c0663b48c7e0b2e7c6ed975e1a8bc2a8c))
* **cache:** add typed result records ([1819841](https://github.com/chio-labs/fensu/commit/181984166af6f4758ca07e95965ad11895fc3fac))
* **cache:** capture file evaluation inputs ([fde9143](https://github.com/chio-labs/fensu/commit/fde9143259aa0183c28e919dd286e1c368612429))
* **cache:** enable persistent checks by default ([35e52d1](https://github.com/chio-labs/fensu/commit/35e52d18d907b1d8c57dd15bfbd6a42ebca43b37))
* **cache:** expose transactional persistent checks ([bd89f7d](https://github.com/chio-labs/fensu/commit/bd89f7d6b59783a6eb6edea73439c23a03014b82))
* **cache:** reuse dependency-aware file results ([74b2a86](https://github.com/chio-labs/fensu/commit/74b2a868c25f2595e3f99df534a603dc8f453eb0))
* **cache:** scope caching per rule with declared cacheability ([800d57c](https://github.com/chio-labs/fensu/commit/800d57c2ff1bac56523a622d67a78b37eb213334))
* **cache:** scope caching per rule with declared cacheability ([5e3dde5](https://github.com/chio-labs/fensu/commit/5e3dde5a0aadcb9fde7a87c00981b026cdc7bdec))
* **cache:** sweep generations and degrade publication failures ([115d9e5](https://github.com/chio-labs/fensu/commit/115d9e520346cf03e9f1908818c4dd43e98b47f6))
* **cache:** verify custom rules under a require-cacheable policy ([850928e](https://github.com/chio-labs/fensu/commit/850928e32cdbaf07c7b5dc2650d8203f12b0e683))
* **checkers:** add generic package naming rule ([fa45dc2](https://github.com/chio-labs/fensu/commit/fa45dc2e3b6ef20a98006f63cb44ca32fcdadff5))
* **checkers:** add keyword-only parameter rule ([2628559](https://github.com/chio-labs/fensu/commit/26285595b4eafb7ddd67e773bc6e34d95e02d032))
* **cli:** add repository-aware skills update ([af83175](https://github.com/chio-labs/fensu/commit/af83175c2e264629835520d311f747622827bdc4))
* **cli:** add rule skill and map commands ([285fd20](https://github.com/chio-labs/fensu/commit/285fd20fd262794a906b827c2ea65479106b50ea))
* **cli:** add ruleset loading and check command ([50df774](https://github.com/chio-labs/fensu/commit/50df774aec954f559ffc0728fc497bbbf35517b7))
* **cli:** flatten skills command and method selectors ([7de134c](https://github.com/chio-labs/fensu/commit/7de134c913eed73315e45de5347e98995a3036af))
* **cli:** flatten skills command and method selectors ([9bd6942](https://github.com/chio-labs/fensu/commit/9bd6942553984fda1dcdd4f59662e29155802fb5))
* **cli:** prioritize actionable check output ([d85924f](https://github.com/chio-labs/fensu/commit/d85924f6b095dee8a9e7fe8e98ddf9b96f685bf2))
* **cli:** prioritize actionable check output ([79167f5](https://github.com/chio-labs/fensu/commit/79167f5bb3bcafd752ecead5d2060fae5377e11d))
* **cli:** refine map styling and skills workflow ([b01cc80](https://github.com/chio-labs/fensu/commit/b01cc80857e74324dad0a95b6062a50528d0f10d))
* **cli:** refine terminal presentation ([1849f81](https://github.com/chio-labs/fensu/commit/1849f81bf430fc0c46fec73e3ea8c5c40b08a19b))
* **cli:** ship native strata executable ([8b0c71b](https://github.com/chio-labs/fensu/commit/8b0c71bb6108d7d449fca56e97f7a15c53a5ebff))
* complete self-hosting cutover ([ea575f4](https://github.com/chio-labs/fensu/commit/ea575f442e0524fe0c2440089af21da35b7d21c8))
* **config:** add configuration loading ([9e7946a](https://github.com/chio-labs/fensu/commit/9e7946acf5aa23c90149718a6954134817032e87))
* **config:** add symbol-scoped rule exceptions ([3fcc994](https://github.com/chio-labs/fensu/commit/3fcc994aae94c5d5d24d685ada182c8533ead2ae))
* **config:** add symbol-scoped rule exceptions ([dd4cb24](https://github.com/chio-labs/fensu/commit/dd4cb2416d382cbd73b200270da285a2d01ff67f))
* **discovery:** add config-driven discovery ([25b7d89](https://github.com/chio-labs/fensu/commit/25b7d89d0333744b0ea162943a04f11216b782ee))
* **discovery:** add native repository snapshot with canonical path and hash table ([4e0377b](https://github.com/chio-labs/fensu/commit/4e0377babbb39857aa538c83475d53f508b76f74))
* enable strata self-hosting ([e41e221](https://github.com/chio-labs/fensu/commit/e41e2219048fbaa34b3005377c7d6a8ac078d7dd))
* **evaluation:** add engine and rule context ([9e366f4](https://github.com/chio-labs/fensu/commit/9e366f4edb53ff2a0cf27836734aeef4b6efafa6))
* **evaluation:** add include and exclude paths ([465fee7](https://github.com/chio-labs/fensu/commit/465fee7f5fe4961b9b24bed4cfde9703de8d7317))
* **evaluation:** add include and exclude paths ([ae95857](https://github.com/chio-labs/fensu/commit/ae95857e9708fe5585fb31f471d88d388d0bae52))
* **evaluation:** add shared analysis foundation ([19a5aa1](https://github.com/chio-labs/fensu/commit/19a5aa1e9895818f4722eb4314434f6e44ae858d))
* **evaluation:** make CPython AST lazy and prewarm native parses in parallel ([db72898](https://github.com/chio-labs/fensu/commit/db728981959f0b3b1c82d80cdabe6716d8a85234))
* **evaluation:** return project dependencies ([ea9b33b](https://github.com/chio-labs/fensu/commit/ea9b33b16b64df124f5ad0cc25524cc8bfc6a6e5))
* **exceptions:** support file-level rule exceptions ([2419d00](https://github.com/chio-labs/fensu/commit/2419d002a76974f80720cbb1859725a2281f665b))
* **exceptions:** support file-level rule exceptions ([73df930](https://github.com/chio-labs/fensu/commit/73df93059c278ea48038183fbf25bc4861b831da))
* expand mapping and diagnostics ([5f30d71](https://github.com/chio-labs/fensu/commit/5f30d71d944c96f014b4a406bab9eb580770acfa))
* **facts:** add strict native parser with CPython validity agreement ([06c0361](https://github.com/chio-labs/fensu/commit/06c03612c2338999f6a1e9a2045cfdf63d840474))
* **facts:** port harness fact families and close native parity ([8eaf1e0](https://github.com/chio-labs/fensu/commit/8eaf1e0e93bccb017cc99e51ead588c862448aaa))
* **facts:** port seventeen fact families to the native backend ([3be79ff](https://github.com/chio-labs/fensu/commit/3be79ff1c7c5a64d4fd56f6d3055c1c2841ee4f6))
* **init:** add guided project setup ([77d1d72](https://github.com/chio-labs/fensu/commit/77d1d7252f1a62318f28458e6889027e436a439c))
* **init:** add memory opt-in ([83ed460](https://github.com/chio-labs/fensu/commit/83ed4600ec06196d5db034a51c174cb1e09de248))
* **init:** enforce the default posture ([108a9d5](https://github.com/chio-labs/fensu/commit/108a9d506d75f4bd9c76f708d6ef00253e63ddca))
* **init:** enforce the default posture ([775bd22](https://github.com/chio-labs/fensu/commit/775bd2246aecd2d39d848c4aa648e6076bd40b96))
* **init:** make setup idempotent and cache-clean ([2c1fa25](https://github.com/chio-labs/fensu/commit/2c1fa25a5c7303b127b49bc5fbd5b029b8e0b299))
* **instrumentation:** add operation counters with corpus-backed invariants ([a10b1b8](https://github.com/chio-labs/fensu/commit/a10b1b85a3cfda473a74921b81fb81597ad790ef))
* **layers:** enforce main entry visibility ([989dd6e](https://github.com/chio-labs/fensu/commit/989dd6edef8c93a067ab25e31097b3e624c84519))
* **layers:** enforce main entry visibility ([3438dce](https://github.com/chio-labs/fensu/commit/3438dced68673d9836bf07a7e11cd6291f97b977))
* **mapping:** resolve unique nominal protocol dispatch ([c519a28](https://github.com/chio-labs/fensu/commit/c519a289b7af457011deb145661f671900fb97e6))
* **mapping:** resolve unique nominal protocol dispatch ([2f1c5c2](https://github.com/chio-labs/fensu/commit/2f1c5c2909e450330c2b14627efaa720b5dd0808))
* **map:** resolve concrete method calls ([333b1da](https://github.com/chio-labs/fensu/commit/333b1da71f75fac3713bcc90fb64d187417db3a8))
* **map:** resolve concrete method calls ([d3d96ff](https://github.com/chio-labs/fensu/commit/d3d96ff7c553bef0bdddc71ec2a92b0d1cedec76))
* **memory:** add bounded graph retrieval ([4176687](https://github.com/chio-labs/fensu/commit/4176687a62e5afe066f4aba98585ce396bb96e4a))
* **memory:** add repository memory foundation ([49616a7](https://github.com/chio-labs/fensu/commit/49616a789c6e3a1994742dac02bc3948344692b1))
* **memory:** add safe archival workflow ([2448fe4](https://github.com/chio-labs/fensu/commit/2448fe4e244753c7ade340a6fb7b5bf7732f3c31))
* **memory:** classify Git visibility ([91f05b3](https://github.com/chio-labs/fensu/commit/91f05b3eb2e89d20ec9d04a9b347879adb99f2d7))
* **memory:** harden private preview ([bd9874d](https://github.com/chio-labs/fensu/commit/bd9874d9a7efdfa2c039138535f77859e7f9c397))
* **memory:** integrate source validation ([a41a90d](https://github.com/chio-labs/fensu/commit/a41a90d52b15cfed3e949c212c7fb5758301ec75))
* **memory:** replace DuckDB with SQLite ([fd07e72](https://github.com/chio-labs/fensu/commit/fd07e728acdf63f5777585a929685cf7567e0cfc))
* **roles:** detect shared domain prefixes ([00bf747](https://github.com/chio-labs/fensu/commit/00bf747e0bc1a499e93307e7d4bca391696c3522))
* **roles:** enforce leaf and helper ownership ([42775b5](https://github.com/chio-labs/fensu/commit/42775b51d4aa916cb671511acda903c17033e0c2))
* **roles:** enforce leaf-or-branch domains ([539169e](https://github.com/chio-labs/fensu/commit/539169e129684971d557666057a1d362ba0f1eeb))
* **rules:** add annotations family ([8faf963](https://github.com/chio-labs/fensu/commit/8faf96300966791119708decbf0f7b5628add74d))
* **rules:** add hygiene family ([c65e37b](https://github.com/chio-labs/fensu/commit/c65e37b3821edf41fe7a4df4c9013b419489314b))
* **rules:** add layers family ([70fb57e](https://github.com/chio-labs/fensu/commit/70fb57e614f4cae15ad4e65b2ed1dc5eddbbfe87))
* **rules:** add naming contract rules ([69cd135](https://github.com/chio-labs/fensu/commit/69cd135e0b10707b508eb8fe53aaec004340b623))
* **rules:** add role layout rules ([47c4b03](https://github.com/chio-labs/fensu/commit/47c4b033a2cd5b0cf64eb30fdda527d390a73d9d))
* **rules:** add role ownership rules ([a495285](https://github.com/chio-labs/fensu/commit/a495285bbd03fe5b7a90f201984dcca77a4c5c2e))
* **rules:** add role surface and shape rules ([eeb9a6d](https://github.com/chio-labs/fensu/commit/eeb9a6dfd1d92c206298f6834ebdda7dfd74957c))
* **rules:** add shape family ([92d2b53](https://github.com/chio-labs/fensu/commit/92d2b5302303ee02e7424a6b15319b1c3c70f72d))
* **rules:** add tests family ([84a941b](https://github.com/chio-labs/fensu/commit/84a941b61db9ebbf9495b01c567107305405bef7))
* **rules:** enable decision literal checks ([573ddfb](https://github.com/chio-labs/fensu/commit/573ddfb9dea60058458ef08ca698fb7c6ad482ed))
* **rules:** enforce custom rule test coverage ([4cd72b3](https://github.com/chio-labs/fensu/commit/4cd72b3960a8b6621857699426eb855e12cbe818))
* **rules:** enforce domain package names ([bff9a51](https://github.com/chio-labs/fensu/commit/bff9a51d82bd2024ab9275cff10091cfe58bd002))
* **rules:** enforce hermetic rule execution ([0e2dedf](https://github.com/chio-labs/fensu/commit/0e2dedf98e7c6fed04bc626bc1f454a5e6e5ccc5))
* **rules:** enforce readable control flow ([3115db5](https://github.com/chio-labs/fensu/commit/3115db5f0a2bf7b5f378c7762a809fa5b16594dc))
* **rules:** enforce tooling structure and decision literals ([6609207](https://github.com/chio-labs/fensu/commit/66092072cd408065da723c485f427635c01e961e))
* **rules:** expand naming and local annotation contracts ([9088012](https://github.com/chio-labs/fensu/commit/90880124ee679304a03402bbfc0234f381cdaaec))
* **rules:** expand naming and local annotation contracts ([9d9184f](https://github.com/chio-labs/fensu/commit/9d9184feaaa95f5c8d515414c6c8fb939a6b72fd))
* **rules:** expose public analysis zones ([7a8d15a](https://github.com/chio-labs/fensu/commit/7a8d15a9deeea772236783d2724add08fe6c4171))
* **rules:** expose public analysis zones ([57c12d0](https://github.com/chio-labs/fensu/commit/57c12d040b158bef3fa1182bbfaf09717fe51697))
* **rules:** organize test rule codes by concern ([def7a2b](https://github.com/chio-labs/fensu/commit/def7a2bf2ba4ca3c1c2e4675342f188534a2843b))
* **skills:** synchronize project bundles ([e399914](https://github.com/chio-labs/fensu/commit/e3999145a8b26df8b56433d19b9ad89b7e17776a))
* **taxonomy:** settle pre-release rule contracts ([bbb24f7](https://github.com/chio-labs/fensu/commit/bbb24f79e28ba2536f9a608ad3e9de8ff74e20dc))
* **taxonomy:** settle pre-release rule contracts ([5f39ad8](https://github.com/chio-labs/fensu/commit/5f39ad8eb167c9579dd441889dbdd57e91feeca9))
* **tooling:** add deterministic performance corpus generator ([b3e2a79](https://github.com/chio-labs/fensu/commit/b3e2a7916c6bd044e4426bad8a032f204a780fdd))
* **tooling:** add fault-dense budget scenarios ([296edd9](https://github.com/chio-labs/fensu/commit/296edd95dcea6a824eb02ce39639c1f1d2eb0438))
* **tooling:** add Rust workspace structure checker ([b3b4f45](https://github.com/chio-labs/fensu/commit/b3b4f459eb2073961432658dfc26a6df175659a5))
* **tooling:** enforce native-backend performance budgets ([a5c4f58](https://github.com/chio-labs/fensu/commit/a5c4f587e268a1ce9fd72e9dbc8deefce29aaf68))
* **tooling:** enforce wall-clock performance budgets in CI ([c431cf2](https://github.com/chio-labs/fensu/commit/c431cf2c898738fea652a1d2ce91e26c1a0524b2))
* **tooling:** harden Rust structure checks ([23edb8a](https://github.com/chio-labs/fensu/commit/23edb8ac7dbe5cac2111c75296bd15e9ab1eeebe))
* **tooling:** tighten native budget ceilings to measured CI reality ([0e5464a](https://github.com/chio-labs/fensu/commit/0e5464a3809256d5b09a55fd707b97149fa3b98f))
* **workflow:** add agent-guided policy foundations ([94303bc](https://github.com/chio-labs/fensu/commit/94303bc7550996d30061ad2b2886c58970b56275))
* **workflow:** add project-aware skills and rule harness ([21cc7c4](https://github.com/chio-labs/fensu/commit/21cc7c4ec4e2e473dc721b1cd5192ddb19685a9d))


### Bug Fixes

* **analysis:** remove duplicate Python fact backend ([c4acc84](https://github.com/chio-labs/fensu/commit/c4acc84afeae75df9c922edc5b25ead0faa0adfe))
* **analysis:** remove duplicate Python fact backend ([912c712](https://github.com/chio-labs/fensu/commit/912c712784fa9ced16118fdd8bca586370a85490))
* **cache:** accept one concurrent publisher ([76db4da](https://github.com/chio-labs/fensu/commit/76db4da06e966493dc72d315934db24104d78124))
* **checkers:** allow TYPE_CHECKING import blocks ([6eab87e](https://github.com/chio-labs/fensu/commit/6eab87ee5ae3ee8591b79a8583beebdcfe8628b3))
* **checkers:** enforce domain role placement ([3a0a2ec](https://github.com/chio-labs/fensu/commit/3a0a2ec785a1f6578ed6d2f32eb138f2baeeb82f))
* **cli:** preserve native output parity ([cf862db](https://github.com/chio-labs/fensu/commit/cf862db40cc4a2811b3038dc7371d26ec34db190))
* **cli:** restore cross-platform native parity ([735eef9](https://github.com/chio-labs/fensu/commit/735eef942653ea6e078648c7a3914d623c3af658))
* **config:** honor configured project layouts ([44cf549](https://github.com/chio-labs/fensu/commit/44cf549cae693905f4bc43e969baf7b89c3b5ba5))
* **docs:** document wheel platforms and the rust toolchain requirement ([7257bf4](https://github.com/chio-labs/fensu/commit/7257bf4a6d9094b2dfc416ffc08f4115ceb8b652))
* **docs:** document wheel platforms and the rust toolchain requirement ([c6edc0a](https://github.com/chio-labs/fensu/commit/c6edc0a21c78e0ada5983c8b87fdd3b2209f1c34))
* **layers:** infer structural import ownership ([733c4cb](https://github.com/chio-labs/fensu/commit/733c4cb1dad85c2c425b7320700f4fd366ccbd0f))
* **layers:** infer structural import ownership ([0fde46a](https://github.com/chio-labs/fensu/commit/0fde46a81dfd2d78bc4c1a890c8b03c4a4dbf998))
* **memory:** close proof database readers ([1a0a5bc](https://github.com/chio-labs/fensu/commit/1a0a5bcfb640ad7f04ace2584f74884abd6baa97))
* **memory:** correct platform proof cases ([3f492de](https://github.com/chio-labs/fensu/commit/3f492de3ac7db5652ce1511d683f35ca9da98ad7))
* **packaging:** separate CLI from Python linkage ([9d910a1](https://github.com/chio-labs/fensu/commit/9d910a190157eaedcd3577dfba82bbc748b3e0d0))
* **reporting:** render repository paths with posix separators on every platform ([31ca3b7](https://github.com/chio-labs/fensu/commit/31ca3b78ca181dcbae816335da39496c79bc6c93))
* **rules:** type custom family selector ([8995f84](https://github.com/chio-labs/fensu/commit/8995f840eb8305670cc0324d3dd76f1366e1396a))
* **scaffolding:** guard O_NONBLOCK for platforms without it ([ff41bcd](https://github.com/chio-labs/fensu/commit/ff41bcdfae035b5ea51842c45b2c166153d35124))
* **scaffolding:** guard O_NONBLOCK for platforms without it ([894696c](https://github.com/chio-labs/fensu/commit/894696c4e6ceb542608f6f5caaa2be6f7787a003))
* **scaffolding:** make descriptor io, rollback, and map selectors windows-safe ([ca4cae8](https://github.com/chio-labs/fensu/commit/ca4cae82ad68485e82465a6c8ccb3e1b81d9b929))
* **scaffolding:** refuse symlinks and directories portably when capturing files ([1aa051e](https://github.com/chio-labs/fensu/commit/1aa051e808ffccf55ecfd8dbf5f990d98a338603))
* **shape:** enforce keyword-only threshold placement ([edaa69a](https://github.com/chio-labs/fensu/commit/edaa69a32f45639e34f61a50a48c34124912157a))
* **shape:** enforce keyword-only threshold placement ([01dccd1](https://github.com/chio-labs/fensu/commit/01dccd1318868f7f4e96110879ae3c4e47a092a4))
* **skills:** support Windows file replacement ([94a82dd](https://github.com/chio-labs/fensu/commit/94a82dda1d40b0bc0fb7a137927b90efceaff61c))
* **taxonomy:** close container and override gaps ([0fb18d8](https://github.com/chio-labs/fensu/commit/0fb18d87d0112da1c67bbae5fdc64bcbbbd61de2))
* **taxonomy:** close container and override gaps ([7da5d4e](https://github.com/chio-labs/fensu/commit/7da5d4e38cfe32be29c02cbc5a7ccdbceac1c212))
* **tests:** import the native extension lazily in parity helpers ([f3fa12f](https://github.com/chio-labs/fensu/commit/f3fa12f1dda84443ef4b9c0aae3ad9f79045adb6))
* **tests:** skip native delegation coverage without the extension ([7def24f](https://github.com/chio-labs/fensu/commit/7def24fd6b311984e03545ea9156f65163b6c8a9))
* **windows:** make output and config publication portable ([240b261](https://github.com/chio-labs/fensu/commit/240b261164a57f8dad8df9015c28e2a492538e0f))
* **windows:** normalize paths and portable test contracts ([bafad7a](https://github.com/chio-labs/fensu/commit/bafad7a6858e69da047d595ef4e1a734c07585b9))


### Performance Improvements

* accelerate repository replay and startup ([2dfe3f9](https://github.com/chio-labs/fensu/commit/2dfe3f9dd38a5395819f1b033d09b595f4a00d3c))
* add public execution owners and shared SFT issue discovery ([038daf3](https://github.com/chio-labs/fensu/commit/038daf3ac766939d8cc79c5a199b97f794e9338b))
* **analysis:** narrow semantic fact traversal ([32dc1c7](https://github.com/chio-labs/fensu/commit/32dc1c7b91a7bdd8354dae290ce2a9f40571f8a1))
* **analysis:** reduce repeated fact traversal ([dfb142a](https://github.com/chio-labs/fensu/commit/dfb142a7f29a65236b7cd4c9944d8cd749f26bf4))
* **analysis:** retain test type facts only ([cee2e7c](https://github.com/chio-labs/fensu/commit/cee2e7c66653331d085c99159395f436b7a31345))
* **budget:** cover startup and initialization ([8e8a786](https://github.com/chio-labs/fensu/commit/8e8a7860b5f9582db63a3da719cd200f828909c2))
* **cache:** bound high-churn publication ([26692f2](https://github.com/chio-labs/fensu/commit/26692f2529e1fca14ad59e37c5c454543afca571))
* **cache:** encode and validate each publication record once ([ad6420a](https://github.com/chio-labs/fensu/commit/ad6420a7ce8a11bb7feabb2e19f976995fe19789))
* **cache:** finish native replay and publication ([ba4949a](https://github.com/chio-labs/fensu/commit/ba4949aa13c1da79bb62d4fe5d0b65ae3ea5a09b))
* **cache:** move storage and warm replay to Rust ([b40c7f2](https://github.com/chio-labs/fensu/commit/b40c7f2295f8068dd663c4017fee57b1e99fc6d1))
* **cache:** remove quadratic dependency scans and pathlib churn ([1e34299](https://github.com/chio-labs/fensu/commit/1e34299f4fcf527da8a63ec3dee98798948ee13e))
* **cache:** remove quadratic dependency scans and pathlib churn ([aa6ac50](https://github.com/chio-labs/fensu/commit/aa6ac50e6819a8a5d2a9f489e6dbee81c7e8f408))
* **cache:** replay aggregated observations to skip record decode on warm runs ([816f35f](https://github.com/chio-labs/fensu/commit/816f35f134068d77c57574e016ca002d9268f55b))
* **cache:** replay one-edit runs from a sparse collection aggregate ([abca86e](https://github.com/chio-labs/fensu/commit/abca86e725b0cb2af34d6db7b8b2d2e2c9d330e7))
* **cache:** reuse implementation path scan ([9076cdd](https://github.com/chio-labs/fensu/commit/9076cdd94c46faad48fe3c72d4f054615c580181))
* **cache:** reuse wheel RECORD fingerprint ([b3acbc4](https://github.com/chio-labs/fensu/commit/b3acbc45e4630b9ef126c82275f2b66f413d656c))
* **cache:** short-circuit unchanged warm checks with stored output ([ef51060](https://github.com/chio-labs/fensu/commit/ef510601e9a4c4cbdc733309a46900b4dd027392))
* **cache:** validate warm manifest once ([48f6b64](https://github.com/chio-labs/fensu/commit/48f6b6420facdce5ee6756c6d6c5c2ae8dbd6742))
* **cache:** verify records by stored-bytes identity instead of re-encoding ([f5ee5a1](https://github.com/chio-labs/fensu/commit/f5ee5a146f3e1706d2a15ac4381c85ffcabd6555))
* **config:** compile path patterns once instead of per match ([c11d227](https://github.com/chio-labs/fensu/commit/c11d2276817957713ec95524edb9c1632e76c81b))
* **custom-rules:** profile external rule packages ([cb4040b](https://github.com/chio-labs/fensu/commit/cb4040bfe61864e4a888b7eb7c711e9552d423c0))
* default full evaluations to automatic worker parallelism ([6037bad](https://github.com/chio-labs/fensu/commit/6037bad761353a1530b7201fa80667f3048fd17a))
* establish shared performance foundation ([6b29450](https://github.com/chio-labs/fensu/commit/6b294506795cb8911dfd10a089bf65eb43810f1b))
* evaluate no-cache checks across parallel worker partitions ([bbc7354](https://github.com/chio-labs/fensu/commit/bbc73547509e5a366618023d746c21a6bc9061a8))
* **evaluation:** cut path churn and duplicate probe work on the uncached floor ([cf98316](https://github.com/chio-labs/fensu/commit/cf983169e8ac26514967f9c1c282a600e66aabe0))
* **evaluation:** match rule exceptions once per file instead of per rule ([ad000e3](https://github.com/chio-labs/fensu/commit/ad000e3d71a8970ede6370385550e9ef1c8bed25))
* **evaluation:** move execution planning to Rust ([7330793](https://github.com/chio-labs/fensu/commit/733079374789c53e11e2f6cd1daa689e731fd596))
* **evaluation:** remove repeated path, threshold, render, and encode work on hot check paths ([9fa37ae](https://github.com/chio-labs/fensu/commit/9fa37aea719c00f38aeb8bdbf5022b8adf700713))
* **evaluation:** reuse prewarmed project analysis ([d892daa](https://github.com/chio-labs/fensu/commit/d892daa75202860f9b9747fb3d7ecd9644cd7d21))
* extract native fact rows in parallel prewarm batches ([6dd3db3](https://github.com/chio-labs/fensu/commit/6dd3db3c95dcc52220fad3174fc1ad58af1b816e))
* **init:** seed cache with parallel evaluation ([6bc5bf8](https://github.com/chio-labs/fensu/commit/6bc5bf8c54938b4229ab311f2b190b6b109cbfdc))
* **instrumentation:** attribute repository query costs ([a1cfcd3](https://github.com/chio-labs/fensu/commit/a1cfcd328fe26f31dc674f577f15969a03d7e1a2))
* **map:** cache project declaration indexes ([4d58c75](https://github.com/chio-labs/fensu/commit/4d58c75ba376992260291485c53ba3827d5d8b26))
* **map:** cache project declaration indexes ([cb72ac1](https://github.com/chio-labs/fensu/commit/cb72ac143754798ed6fba3207882529893d50d71))
* **map:** move index substrate to Rust ([a3142f2](https://github.com/chio-labs/fensu/commit/a3142f2d3f9aac5fd99b2776fb8153f37b3c74a4))
* **memory:** bulk publish DuckDB rows ([8de5c3e](https://github.com/chio-labs/fensu/commit/8de5c3ef3766f55475558c97aa04b10908040eb7))
* **memory:** vectorize large corpus publication ([b30c7a7](https://github.com/chio-labs/fensu/commit/b30c7a7eac6090a8e6753775d9fb78d2b3929358))
* reduce repeated analysis work ([61f769f](https://github.com/chio-labs/fensu/commit/61f769ff60b896341ffa716c076c4153125e5be1))
* **reporting:** read excerpted sources once per file, not per fault ([7ae1614](https://github.com/chio-labs/fensu/commit/7ae16148dd854419ae954ff1039f0874d7a762c6))
* **rules:** execute SFA001 natively ([30de82c](https://github.com/chio-labs/fensu/commit/30de82c359861c2f433faae35492672dc31dc402))
* **rules:** finish native file-rule execution ([ccc9de8](https://github.com/chio-labs/fensu/commit/ccc9de8990fa41062eaf7492f597d3f6a030ecd7))
* **rules:** port aggregate core rules to Rust ([72e0788](https://github.com/chio-labs/fensu/commit/72e0788a753b33cfccb8d2a8b3a03f10b28389e6))
* **rules:** port annotation family to Rust ([2c5388b](https://github.com/chio-labs/fensu/commit/2c5388b2a5152068f465a685b68104aab03f5eae))
* **rules:** port hygiene family to Rust ([0d33460](https://github.com/chio-labs/fensu/commit/0d334600f0b8a94ed19ab933667b39692dcb577f))
* **rules:** port local layer policies to Rust ([e3870d9](https://github.com/chio-labs/fensu/commit/e3870d92c355fed51b6c9d8376c52746b0eceeeb))
* **rules:** port local role policies to Rust ([bbaf4e3](https://github.com/chio-labs/fensu/commit/bbaf4e3c894e99253b0a690ca9761c499d252bcc))
* **rules:** port local shape rules to Rust ([3b9fedf](https://github.com/chio-labs/fensu/commit/3b9fedf2c48328289c255326150d89cbb5e4d598))
* **rules:** port local test policies to Rust ([af8df62](https://github.com/chio-labs/fensu/commit/af8df62c1b46a187e5c0097262fcd1d0018f90b7))
* **rules:** port naming family to Rust ([955ca40](https://github.com/chio-labs/fensu/commit/955ca408557f7410b08b7cd735c835a6c13f1237))
* **rules:** port role-gated shape rules to Rust ([536365d](https://github.com/chio-labs/fensu/commit/536365d7d5646af5c0006bc6ff710f5c405ee9da))
* **rules:** port shared-fact file rules to Rust ([d6a7251](https://github.com/chio-labs/fensu/commit/d6a72511d0c1a84fe014d6f2480d71a2cac76bd9))
* **rules:** port threshold shape rules to Rust ([4b54149](https://github.com/chio-labs/fensu/commit/4b54149419834d01a7b61f5ea0e96c05bc94c14c))


### Documentation

* align package tagline ([7d2ad5e](https://github.com/chio-labs/fensu/commit/7d2ad5e0a7546d10f8519977fb15386c6b8c2df3))
* align package tagline ([fbf65d9](https://github.com/chio-labs/fensu/commit/fbf65d99115872adbba3c230b70dce18b93ca7da))
* improve package presentation ([7f63abe](https://github.com/chio-labs/fensu/commit/7f63abe35d3044b5d6ff5bf280d51a0badd0ada3))
* improve package presentation ([a644413](https://github.com/chio-labs/fensu/commit/a644413936476636f4bd4f0b8c29aef919494a60))
* **memory:** announce repository workflows ([4614502](https://github.com/chio-labs/fensu/commit/4614502e97405f3f13f896cf16254608def7d548))
* remove development footer ([53c07b8](https://github.com/chio-labs/fensu/commit/53c07b8bf5eedd1d1e5b266c7263804a3a660e9c))
* **rules:** standardize the custom rule package path ([6b9edf3](https://github.com/chio-labs/fensu/commit/6b9edf3bc7ae189e7bdd2342cd75e8389a35d457))
* show strata map call tree ([96f77f2](https://github.com/chio-labs/fensu/commit/96f77f23290bafe226965f87b803707fb1bc911a))
* streamline project readme ([21c0c36](https://github.com/chio-labs/fensu/commit/21c0c3601533bf27dbb0dd13db35ad0fa5f4c207))
* streamline project readme ([c09c8a3](https://github.com/chio-labs/fensu/commit/c09c8a3e5f1150c774e5d7f460348364216f82dc))

## 0.1.0

- Initial functional Fensu release, continuing the implementation history developed as Strata.
