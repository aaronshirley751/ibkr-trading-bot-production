# CI Run Metadata
- Run ID: 21741564420
- Job ID: 62717959294
- Run URL: https://github.com/aaronshirley751/ibkr-trading-bot-production/actions/runs/21741564420
- Job URL: https://github.com/aaronshirley751/ibkr-trading-bot-production/actions/runs/21741564420/job/62717959294

2026-02-06T06:49:04.4191668Z Current runner version: '2.331.0'
2026-02-06T06:49:04.4217282Z ##[group]Runner Image Provisioner
2026-02-06T06:49:04.4218171Z Hosted Compute Agent
2026-02-06T06:49:04.4218873Z Version: 20260123.484
2026-02-06T06:49:04.4219427Z Commit: 6bd6555ca37d84114959e1c76d2c01448ff61c5d
2026-02-06T06:49:04.4220090Z Build Date: 2026-01-23T19:41:17Z
2026-02-06T06:49:04.4221109Z Worker ID: {f3f0360c-9d0b-434e-9a79-272d54552e3f}
2026-02-06T06:49:04.4221781Z Azure Region: westus
2026-02-06T06:49:04.4222291Z ##[endgroup]
2026-02-06T06:49:04.4223821Z ##[group]Operating System
2026-02-06T06:49:04.4224411Z Ubuntu
2026-02-06T06:49:04.4224829Z 24.04.3
2026-02-06T06:49:04.4225349Z LTS
2026-02-06T06:49:04.4225789Z ##[endgroup]
2026-02-06T06:49:04.4226260Z ##[group]Runner Image
2026-02-06T06:49:04.4226859Z Image: ubuntu-24.04
2026-02-06T06:49:04.4227323Z Version: 20260201.15.1
2026-02-06T06:49:04.4228446Z Included Software: https://github.com/actions/runner-images/blob/ubuntu24/20260201.15/images/ubuntu/Ubuntu2404-Readme.md
2026-02-06T06:49:04.4229977Z Image Release: https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260201.15
2026-02-06T06:49:04.4231158Z ##[endgroup]
2026-02-06T06:49:04.4232282Z ##[group]GITHUB_TOKEN Permissions
2026-02-06T06:49:04.4234153Z Contents: read
2026-02-06T06:49:04.4234804Z Metadata: read
2026-02-06T06:49:04.4235313Z Packages: read
2026-02-06T06:49:04.4235784Z ##[endgroup]
2026-02-06T06:49:04.4238041Z Secret source: Actions
2026-02-06T06:49:04.4238846Z Prepare workflow directory
2026-02-06T06:49:04.4597347Z Prepare all required actions
2026-02-06T06:49:04.4659354Z Getting action download info
2026-02-06T06:49:04.9675368Z Download action repository 'actions/checkout@v4' (SHA:34e114876b0b11c390a56381ad16ebd13914f8d5)
2026-02-06T06:49:05.0630291Z Download action repository 'actions/setup-python@v5' (SHA:a26af69be951a213d495a4c3e4e4022e16d87065)
2026-02-06T06:49:05.1434894Z Download action repository 'snok/install-poetry@v1' (SHA:76e04a911780d5b312d89783f7b1cd627778900a)
2026-02-06T06:49:05.7399819Z Download action repository 'actions/cache@v4' (SHA:0057852bfaa89a56745cba8c7296529d2fc39830)
2026-02-06T06:49:05.9982454Z Complete job name: quality-checks
2026-02-06T06:49:06.0899349Z ##[group]Run actions/checkout@v4
2026-02-06T06:49:06.0900838Z with:
2026-02-06T06:49:06.0901820Z   repository: aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:49:06.0903405Z   token: ***
2026-02-06T06:49:06.0904129Z   ssh-strict: true
2026-02-06T06:49:06.0904888Z   ssh-user: git
2026-02-06T06:49:06.0905653Z   persist-credentials: true
2026-02-06T06:49:06.0906510Z   clean: true
2026-02-06T06:49:06.0907283Z   sparse-checkout-cone-mode: true
2026-02-06T06:49:06.0908238Z   fetch-depth: 1
2026-02-06T06:49:06.0908980Z   fetch-tags: false
2026-02-06T06:49:06.0909764Z   show-progress: true
2026-02-06T06:49:06.0910738Z   lfs: false
2026-02-06T06:49:06.0911476Z   submodules: false
2026-02-06T06:49:06.0912271Z   set-safe-directory: true
2026-02-06T06:49:06.0913413Z ##[endgroup]
2026-02-06T06:49:06.2059709Z Syncing repository: aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:49:06.2063208Z ##[group]Getting Git version info
2026-02-06T06:49:06.2065054Z Working directory is '/home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production'
2026-02-06T06:49:06.2067738Z [command]/usr/bin/git version
2026-02-06T06:49:06.2186361Z git version 2.52.0
2026-02-06T06:49:06.2213771Z ##[endgroup]
2026-02-06T06:49:06.2231171Z Temporarily overriding HOME='/home/runner/work/_temp/007b9315-10a4-46a4-8e66-d3585e23946d' before making global git config changes
2026-02-06T06:49:06.2245985Z Adding repository directory to the temporary git global config as a safe directory
2026-02-06T06:49:06.2248890Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:49:06.2294762Z Deleting the contents of '/home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production'
2026-02-06T06:49:06.2299175Z ##[group]Initializing the repository
2026-02-06T06:49:06.2304838Z [command]/usr/bin/git init /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:49:06.2420881Z hint: Using 'master' as the name for the initial branch. This default branch name
2026-02-06T06:49:06.2423602Z hint: will change to "main" in Git 3.0. To configure the initial branch name
2026-02-06T06:49:06.2426009Z hint: to use in all of your new repositories, which will suppress this warning,
2026-02-06T06:49:06.2428412Z hint: call:
2026-02-06T06:49:06.2429606Z hint:
2026-02-06T06:49:06.2431818Z hint: 	git config --global init.defaultBranch <name>
2026-02-06T06:49:06.2433686Z hint:
2026-02-06T06:49:06.2435407Z hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
2026-02-06T06:49:06.2438417Z hint: 'development'. The just-created branch can be renamed via this command:
2026-02-06T06:49:06.2441085Z hint:
2026-02-06T06:49:06.2442336Z hint: 	git branch -m <name>
2026-02-06T06:49:06.2443664Z hint:
2026-02-06T06:49:06.2445493Z hint: Disable this message with "git config set advice.defaultBranchName false"
2026-02-06T06:49:06.2448975Z Initialized empty Git repository in /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production/.git/
2026-02-06T06:49:06.2453301Z [command]/usr/bin/git remote add origin https://github.com/aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:49:06.2480893Z ##[endgroup]
2026-02-06T06:49:06.2483212Z ##[group]Disabling automatic garbage collection
2026-02-06T06:49:06.2485544Z [command]/usr/bin/git config --local gc.auto 0
2026-02-06T06:49:06.2519458Z ##[endgroup]
2026-02-06T06:49:06.2520987Z ##[group]Setting up auth
2026-02-06T06:49:06.2527161Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-02-06T06:49:06.2559285Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-02-06T06:49:06.2910184Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-02-06T06:49:06.2946331Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-02-06T06:49:06.3169392Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
2026-02-06T06:49:06.3203207Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
2026-02-06T06:49:06.3440796Z [command]/usr/bin/git config --local http.https://github.com/.extraheader AUTHORIZATION: basic ***
2026-02-06T06:49:06.3476837Z ##[endgroup]
2026-02-06T06:49:06.3478540Z ##[group]Fetching the repository
2026-02-06T06:49:06.3486322Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +cae3b8174b98a787a4d111b82e2f5db2330a1fb5:refs/remotes/origin/main
2026-02-06T06:49:06.9415861Z From https://github.com/aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:49:06.9417874Z  * [new ref]         cae3b8174b98a787a4d111b82e2f5db2330a1fb5 -> origin/main
2026-02-06T06:49:06.9451793Z ##[endgroup]
2026-02-06T06:49:06.9453972Z ##[group]Determining the checkout info
2026-02-06T06:49:06.9456373Z ##[endgroup]
2026-02-06T06:49:06.9460200Z [command]/usr/bin/git sparse-checkout disable
2026-02-06T06:49:06.9508587Z [command]/usr/bin/git config --local --unset-all extensions.worktreeConfig
2026-02-06T06:49:06.9540156Z ##[group]Checking out the ref
2026-02-06T06:49:06.9544862Z [command]/usr/bin/git checkout --progress --force -B main refs/remotes/origin/main
2026-02-06T06:49:06.9626455Z Switched to a new branch 'main'
2026-02-06T06:49:06.9628184Z branch 'main' set up to track 'origin/main'.
2026-02-06T06:49:06.9637679Z ##[endgroup]
2026-02-06T06:49:06.9677138Z [command]/usr/bin/git log -1 --format=%H
2026-02-06T06:49:06.9700239Z cae3b8174b98a787a4d111b82e2f5db2330a1fb5
2026-02-06T06:49:07.0014497Z ##[group]Run actions/setup-python@v5
2026-02-06T06:49:07.0015467Z with:
2026-02-06T06:49:07.0016126Z   python-version: 3.12
2026-02-06T06:49:07.0016889Z   check-latest: false
2026-02-06T06:49:07.0017876Z   token: ***
2026-02-06T06:49:07.0018580Z   update-environment: true
2026-02-06T06:49:07.0019432Z   allow-prereleases: false
2026-02-06T06:49:07.0020253Z   freethreaded: false
2026-02-06T06:49:07.0021161Z ##[endgroup]
2026-02-06T06:49:07.1897049Z ##[group]Installed versions
2026-02-06T06:49:07.2049276Z Successfully set up CPython (3.12.12)
2026-02-06T06:49:07.2050548Z ##[endgroup]
2026-02-06T06:49:07.2272563Z ##[group]Run snok/install-poetry@v1
2026-02-06T06:49:07.2272938Z with:
2026-02-06T06:49:07.2273177Z   version: 2.3.2
2026-02-06T06:49:07.2273443Z   virtualenvs-create: true
2026-02-06T06:49:07.2273744Z   virtualenvs-in-project: true
2026-02-06T06:49:07.2274077Z   virtualenvs-path: {cache-dir}/virtualenvs
2026-02-06T06:49:07.2274426Z   installer-parallel: true
2026-02-06T06:49:07.2274718Z env:
2026-02-06T06:49:07.2275020Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2275567Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:07.2276084Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2276540Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2276999Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2277455Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:07.2277842Z ##[endgroup]
2026-02-06T06:49:07.2363882Z ##[group]Run $GITHUB_ACTION_PATH/main.sh
2026-02-06T06:49:07.2364363Z [36;1m$GITHUB_ACTION_PATH/main.sh[0m
2026-02-06T06:49:07.2469489Z shell: /usr/bin/bash --noprofile --norc -e -o pipefail {0}
2026-02-06T06:49:07.2469965Z env:
2026-02-06T06:49:07.2470463Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2470999Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:07.2471544Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2472003Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2472517Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:07.2473069Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:07.2473465Z   VERSION: 2.3.2
2026-02-06T06:49:07.2473726Z   VIRTUALENVS_CREATE: true
2026-02-06T06:49:07.2474027Z   VIRTUALENVS_IN_PROJECT: true
2026-02-06T06:49:07.2474367Z   VIRTUALENVS_PATH: {cache-dir}/virtualenvs
2026-02-06T06:49:07.2474714Z   INSTALLER_PARALLEL: true
2026-02-06T06:49:07.2475004Z   INSTALLATION_ARGUMENTS:
2026-02-06T06:49:07.2475281Z   POETRY_PLUGINS:
2026-02-06T06:49:07.2475532Z ##[endgroup]
2026-02-06T06:49:08.0927814Z
2026-02-06T06:49:08.0928902Z [33mSetting Poetry installation path as /home/runner/.local[0m
2026-02-06T06:49:08.0929600Z
2026-02-06T06:49:08.0930567Z [33mInstalling Poetry 👷[0m
2026-02-06T06:49:08.0931194Z
2026-02-06T06:49:19.4828022Z Retrieving Poetry metadata
2026-02-06T06:49:19.4828515Z
2026-02-06T06:49:19.4828687Z # Welcome to Poetry!
2026-02-06T06:49:19.4828918Z
2026-02-06T06:49:19.4829187Z This will download and install the latest version of Poetry,
2026-02-06T06:49:19.4829814Z a dependency and package manager for Python.
2026-02-06T06:49:19.4830186Z
2026-02-06T06:49:19.4830779Z It will add the `poetry` command to Poetry's bin directory, located at:
2026-02-06T06:49:19.4831254Z
2026-02-06T06:49:19.4831431Z /home/runner/.local/bin
2026-02-06T06:49:19.4831742Z
2026-02-06T06:49:19.4832133Z You can uninstall at any time by executing this script with the --uninstall option,
2026-02-06T06:49:19.4832820Z and these changes will be reverted.
2026-02-06T06:49:19.4833106Z
2026-02-06T06:49:19.4833279Z Installing Poetry (2.3.2)
2026-02-06T06:49:19.4833750Z Installing Poetry (2.3.2): Creating environment
2026-02-06T06:49:19.4834439Z Installing Poetry (2.3.2): Installing Poetry
2026-02-06T06:49:19.4835498Z Installing Poetry (2.3.2): Creating script
2026-02-06T06:49:19.4836096Z Installing Poetry (2.3.2): Done
2026-02-06T06:49:19.4836399Z
2026-02-06T06:49:19.4836597Z Poetry (2.3.2) is installed now. Great!
2026-02-06T06:49:19.4836939Z
2026-02-06T06:49:19.4837345Z You can test that everything is set up by executing:
2026-02-06T06:49:19.4837802Z
2026-02-06T06:49:19.4837964Z `poetry --version`
2026-02-06T06:49:19.4838206Z
2026-02-06T06:49:22.3164601Z
2026-02-06T06:49:22.3165667Z [33mInstallation completed. Configuring settings 🛠[0m
2026-02-06T06:49:22.3166197Z
2026-02-06T06:49:22.3166965Z [33mDone ✅[0m
2026-02-06T06:49:22.3167292Z
2026-02-06T06:49:22.3168983Z [33mIf you are creating a venv in your project, you can activate it by running 'source .venv/bin/activate'. If you're running this in an OS matrix, you can use 'source $VENV' instead, as an OS agnostic option[0m
2026-02-06T06:49:22.3981661Z ##[group]Run actions/cache@v4
2026-02-06T06:49:22.3981928Z with:
2026-02-06T06:49:22.3982128Z   path: .venv
2026-02-06T06:49:22.3982470Z   key: venv-Linux-443fe1c6fdf2e8b7fd4ad860fa59f3b8c699cbecd93c25cb52e82fa3f8c958b0
2026-02-06T06:49:22.3982901Z   enableCrossOsArchive: false
2026-02-06T06:49:22.3983137Z   fail-on-cache-miss: false
2026-02-06T06:49:22.3983348Z   lookup-only: false
2026-02-06T06:49:22.3983539Z   save-always: false
2026-02-06T06:49:22.3983710Z env:
2026-02-06T06:49:22.3983943Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.3984338Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:22.3984774Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.3985119Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.3985463Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.3985859Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:22.3986171Z   VENV: .venv/bin/activate
2026-02-06T06:49:22.3986373Z ##[endgroup]
2026-02-06T06:49:22.8776550Z Cache not found for input keys: venv-Linux-443fe1c6fdf2e8b7fd4ad860fa59f3b8c699cbecd93c25cb52e82fa3f8c958b0
2026-02-06T06:49:22.8858341Z ##[group]Run poetry install --no-interaction --no-root
2026-02-06T06:49:22.8858761Z [36;1mpoetry install --no-interaction --no-root[0m
2026-02-06T06:49:22.8895430Z shell: /usr/bin/bash -e {0}
2026-02-06T06:49:22.8895675Z env:
2026-02-06T06:49:22.8895925Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.8896339Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:22.8896748Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.8897094Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.8897450Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:22.8897804Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:22.8898101Z   VENV: .venv/bin/activate
2026-02-06T06:49:22.8898318Z ##[endgroup]
2026-02-06T06:49:23.3867463Z Creating virtualenv ibkr-trading-bot in /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production/.venv
2026-02-06T06:49:23.8733359Z Installing dependencies from lock file
2026-02-06T06:49:24.0577318Z
2026-02-06T06:49:24.0578258Z Package operations: 47 installs, 0 updates, 0 removals
2026-02-06T06:49:24.0578706Z
2026-02-06T06:49:24.0584419Z   - Installing aiohappyeyeballs (2.6.1)
2026-02-06T06:49:24.0594317Z   - Installing aiohttp (3.13.3)
2026-02-06T06:49:24.0596803Z   - Installing aiosignal (1.4.0)
2026-02-06T06:49:24.0603649Z   - Installing annotated-types (0.7.0)
2026-02-06T06:49:24.0620857Z   - Installing attrs (25.4.0)
2026-02-06T06:49:24.0652166Z   - Installing black (26.1.0)
2026-02-06T06:49:24.0668157Z   - Installing cfgv (3.5.0)
2026-02-06T06:49:24.0680256Z   - Installing click (8.3.1)
2026-02-06T06:49:24.2849078Z   - Installing coverage (7.13.3)
2026-02-06T06:49:24.2926579Z   - Installing distlib (0.4.0)
2026-02-06T06:49:24.3517603Z   - Installing eventkit (1.0.3)
2026-02-06T06:49:24.3596197Z   - Installing filelock (3.20.3)
2026-02-06T06:49:24.4361639Z   - Installing frozenlist (1.8.0)
2026-02-06T06:49:24.4814892Z   - Installing ib-insync (0.9.86)
2026-02-06T06:49:24.4926118Z   - Installing identify (2.6.16)
2026-02-06T06:49:24.5560282Z   - Installing idna (3.11)
2026-02-06T06:49:24.5620720Z   - Installing iniconfig (2.3.0)
2026-02-06T06:49:24.5873818Z   - Installing librt (0.7.8)
2026-02-06T06:49:24.6118416Z   - Installing multidict (6.7.1)
2026-02-06T06:49:24.6256121Z   - Installing mypy (1.19.1)
2026-02-06T06:49:24.6262849Z   - Installing mypy-extensions (1.1.0)
2026-02-06T06:49:24.6641659Z   - Installing nest-asyncio (1.6.0)
2026-02-06T06:49:24.6897514Z   - Installing nodeenv (1.10.0)
2026-02-06T06:49:24.7023924Z   - Installing numpy (2.4.2)
2026-02-06T06:49:24.7393406Z   - Installing packaging (26.0)
2026-02-06T06:49:24.7637572Z   - Installing pandas (3.0.0)
2026-02-06T06:49:24.7674306Z   - Installing pathspec (1.0.4)
2026-02-06T06:49:24.8237924Z   - Installing platformdirs (4.5.1)
2026-02-06T06:49:24.8577410Z   - Installing pluggy (1.6.0)
2026-02-06T06:49:24.8958627Z   - Installing pre-commit (4.5.1)
2026-02-06T06:49:24.9146733Z   - Installing propcache (0.4.1)
2026-02-06T06:49:24.9529675Z   - Installing pydantic (2.12.5)
2026-02-06T06:49:25.0579080Z   - Installing pydantic-core (2.41.5)
2026-02-06T06:49:25.1103700Z   - Installing pygments (2.19.2)
2026-02-06T06:49:25.2166931Z   - Installing pytest (9.0.2)
2026-02-06T06:49:25.2551877Z   - Installing pytest-asyncio (1.3.0)
2026-02-06T06:49:25.3151896Z   - Installing pytest-cov (7.0.0)
2026-02-06T06:49:25.3909550Z   - Installing python-dateutil (2.9.0.post0)
2026-02-06T06:49:25.4326008Z   - Installing python-dotenv (1.2.1)
2026-02-06T06:49:25.5091876Z   - Installing pytokens (0.4.1)
2026-02-06T06:49:25.5495565Z   - Installing pyyaml (6.0.3)
2026-02-06T06:49:25.5861506Z   - Installing ruff (0.15.0)
2026-02-06T06:49:25.6690238Z   - Installing six (1.17.0)
2026-02-06T06:49:25.7228857Z   - Installing typing-extensions (4.15.0)
2026-02-06T06:49:25.7288500Z   - Installing typing-inspection (0.4.2)
2026-02-06T06:49:25.7867661Z   - Installing virtualenv (20.36.1)
2026-02-06T06:49:25.7966530Z   - Installing yarl (1.22.0)
2026-02-06T06:49:28.0075668Z ##[group]Run poetry run ruff check src/ tests/
2026-02-06T06:49:28.0076010Z [36;1mpoetry run ruff check src/ tests/[0m
2026-02-06T06:49:28.0108439Z shell: /usr/bin/bash -e {0}
2026-02-06T06:49:28.0108664Z env:
2026-02-06T06:49:28.0108905Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.0109305Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:28.0109697Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.0110056Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.0110590Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.0110956Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:28.0111269Z   VENV: .venv/bin/activate
2026-02-06T06:49:28.0111469Z ##[endgroup]
2026-02-06T06:49:28.5092926Z All checks passed!
2026-02-06T06:49:28.5132879Z ##[group]Run poetry run black --check src/ tests/
2026-02-06T06:49:28.5133254Z [36;1mpoetry run black --check src/ tests/[0m
2026-02-06T06:49:28.5166002Z shell: /usr/bin/bash -e {0}
2026-02-06T06:49:28.5166217Z env:
2026-02-06T06:49:28.5166465Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.5166861Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:28.5167259Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.5167607Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.5167962Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:28.5168310Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:28.5168608Z   VENV: .venv/bin/activate
2026-02-06T06:49:28.5169013Z ##[endgroup]
2026-02-06T06:49:29.4520092Z All done! ✨ 🍰 ✨
2026-02-06T06:49:29.4520694Z 11 files would be left unchanged.
2026-02-06T06:49:29.4800862Z ##[group]Run poetry run mypy src/
2026-02-06T06:49:29.4801172Z [36;1mpoetry run mypy src/[0m
2026-02-06T06:49:29.4832876Z shell: /usr/bin/bash -e {0}
2026-02-06T06:49:29.4833098Z env:
2026-02-06T06:49:29.4833338Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:29.4833737Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:29.4834154Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:29.4834502Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:29.4834853Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:29.4835210Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:29.4835506Z   VENV: .venv/bin/activate
2026-02-06T06:49:29.4835708Z ##[endgroup]
2026-02-06T06:49:31.4365258Z Success: no issues found in 7 source files
2026-02-06T06:49:31.4468975Z ##[group]Run set +e
2026-02-06T06:49:31.4469218Z [36;1mset +e[0m
2026-02-06T06:49:31.4469434Z [36;1mpoetry run pytest tests/ --verbose[0m
2026-02-06T06:49:31.4469697Z [36;1mexit_code=$?[0m
2026-02-06T06:49:31.4469880Z [36;1mset -e[0m
2026-02-06T06:49:31.4470065Z [36;1mif [ $exit_code -eq 5 ]; then[0m
2026-02-06T06:49:31.4470507Z [36;1m  echo "No tests collected."[0m
2026-02-06T06:49:31.4470767Z [36;1m  exit 0[0m
2026-02-06T06:49:31.4470932Z [36;1mfi[0m
2026-02-06T06:49:31.4471100Z [36;1mexit $exit_code[0m
2026-02-06T06:49:31.4503141Z shell: /usr/bin/bash -e {0}
2026-02-06T06:49:31.4503374Z env:
2026-02-06T06:49:31.4503612Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:31.4504016Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:49:31.4504421Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:31.4504773Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:31.4505199Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:49:31.4505556Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:49:31.4505861Z   VENV: .venv/bin/activate
2026-02-06T06:49:31.4506057Z ##[endgroup]
2026-02-06T06:49:32.6600903Z ============================= test session starts ==============================
2026-02-06T06:49:32.6602245Z platform linux -- Python 3.12.12, pytest-9.0.2, pluggy-1.6.0 -- /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production/.venv/bin/python
2026-02-06T06:49:32.6603472Z cachedir: .pytest_cache
2026-02-06T06:49:32.6604137Z rootdir: /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:49:32.6604844Z configfile: pyproject.toml
2026-02-06T06:49:32.6605254Z plugins: cov-7.0.0, asyncio-1.3.0
2026-02-06T06:49:32.6606137Z asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
2026-02-06T06:49:32.6943703Z collecting ... collected 0 items
2026-02-06T06:49:32.6944067Z
2026-02-06T06:49:32.6944293Z ============================ no tests ran in 0.01s =============================
2026-02-06T06:49:32.7216287Z No tests collected.
2026-02-06T06:49:33.2640910Z Post job cleanup.
2026-02-06T06:49:33.4052489Z [command]/usr/bin/tar --posix -cf cache.tzst --exclude cache.tzst -P -C /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production --files-from manifest.txt --use-compress-program zstdmt
2026-02-06T06:49:35.3862645Z Sent 14548992 of 65867307 (22.1%), 13.9 MBs/sec
2026-02-06T06:49:36.3866532Z Sent 65601536 of 65867307 (99.6%), 31.3 MBs/sec
2026-02-06T06:49:36.6696436Z Sent 65867307 of 65867307 (100.0%), 27.5 MBs/sec
2026-02-06T06:49:36.8299043Z Cache saved with key: venv-Linux-443fe1c6fdf2e8b7fd4ad860fa59f3b8c699cbecd93c25cb52e82fa3f8c958b0
2026-02-06T06:49:36.8427123Z Post job cleanup.
2026-02-06T06:49:37.0078634Z Post job cleanup.
2026-02-06T06:49:37.1032888Z [command]/usr/bin/git version
2026-02-06T06:49:37.1070543Z git version 2.52.0
2026-02-06T06:49:37.1113218Z Temporarily overriding HOME='/home/runner/work/_temp/33ff6164-9fed-4b9f-ad54-de7e5535537a' before making global git config changes
2026-02-06T06:49:37.1114475Z Adding repository directory to the temporary git global config as a safe directory
2026-02-06T06:49:37.1127068Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:49:37.1161715Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-02-06T06:49:37.1193836Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-02-06T06:49:37.1431153Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-02-06T06:49:37.1455282Z http.https://github.com/.extraheader
2026-02-06T06:49:37.1468061Z [command]/usr/bin/git config --local --unset-all http.https://github.com/.extraheader
2026-02-06T06:49:37.1501871Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-02-06T06:49:37.1732060Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
2026-02-06T06:49:37.1764895Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
2026-02-06T06:49:37.2107960Z Cleaning up orphan processes
