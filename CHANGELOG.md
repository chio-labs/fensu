# Changelog

## Unreleased

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
