2026-02-06T06:42:25.7525413Z Current runner version: '2.331.0'
2026-02-06T06:42:25.7548554Z ##[group]Runner Image Provisioner
2026-02-06T06:42:25.7549338Z Hosted Compute Agent
2026-02-06T06:42:25.7549891Z Version: 20260123.484
2026-02-06T06:42:25.7550420Z Commit: 6bd6555ca37d84114959e1c76d2c01448ff61c5d
2026-02-06T06:42:25.7551054Z Build Date: 2026-01-23T19:41:17Z
2026-02-06T06:42:25.7551741Z Worker ID: {31ca7898-db52-4166-94f0-f9a57a62f377}
2026-02-06T06:42:25.7552453Z Azure Region: northcentralus
2026-02-06T06:42:25.7553003Z ##[endgroup]
2026-02-06T06:42:25.7554272Z ##[group]Operating System
2026-02-06T06:42:25.7554856Z Ubuntu
2026-02-06T06:42:25.7555252Z 24.04.3
2026-02-06T06:42:25.7555661Z LTS
2026-02-06T06:42:25.7556119Z ##[endgroup]
2026-02-06T06:42:25.7556563Z ##[group]Runner Image
2026-02-06T06:42:25.7557029Z Image: ubuntu-24.04
2026-02-06T06:42:25.7557523Z Version: 20260201.15.1
2026-02-06T06:42:25.7558561Z Included Software: https://github.com/actions/runner-images/blob/ubuntu24/20260201.15/images/ubuntu/Ubuntu2404-Readme.md
2026-02-06T06:42:25.7559888Z Image Release: https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260201.15
2026-02-06T06:42:25.7560646Z ##[endgroup]
2026-02-06T06:42:25.7561762Z ##[group]GITHUB_TOKEN Permissions
2026-02-06T06:42:25.7563609Z Contents: read
2026-02-06T06:42:25.7564084Z Metadata: read
2026-02-06T06:42:25.7564579Z Packages: read
2026-02-06T06:42:25.7565044Z ##[endgroup]
2026-02-06T06:42:25.7567090Z Secret source: Actions
2026-02-06T06:42:25.7567750Z Prepare workflow directory
2026-02-06T06:42:25.7938874Z Prepare all required actions
2026-02-06T06:42:25.7978213Z Getting action download info
2026-02-06T06:42:26.1819151Z Download action repository 'actions/checkout@v4' (SHA:34e114876b0b11c390a56381ad16ebd13914f8d5)
2026-02-06T06:42:27.7991914Z Download action repository 'actions/setup-python@v5' (SHA:a26af69be951a213d495a4c3e4e4022e16d87065)
2026-02-06T06:42:28.0612366Z Download action repository 'snok/install-poetry@v1' (SHA:76e04a911780d5b312d89783f7b1cd627778900a)
2026-02-06T06:42:28.3026345Z Download action repository 'actions/cache@v4' (SHA:0057852bfaa89a56745cba8c7296529d2fc39830)
2026-02-06T06:42:28.8550849Z Complete job name: quality-checks
2026-02-06T06:42:28.9263194Z ##[group]Run actions/checkout@v4
2026-02-06T06:42:28.9263847Z with:
2026-02-06T06:42:28.9264112Z   repository: aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:42:28.9264674Z   token: ***
2026-02-06T06:42:28.9264853Z   ssh-strict: true
2026-02-06T06:42:28.9265031Z   ssh-user: git
2026-02-06T06:42:28.9265215Z   persist-credentials: true
2026-02-06T06:42:28.9265433Z   clean: true
2026-02-06T06:42:28.9265618Z   sparse-checkout-cone-mode: true
2026-02-06T06:42:28.9265847Z   fetch-depth: 1
2026-02-06T06:42:28.9266041Z   fetch-tags: false
2026-02-06T06:42:28.9266222Z   show-progress: true
2026-02-06T06:42:28.9266404Z   lfs: false
2026-02-06T06:42:28.9266579Z   submodules: false
2026-02-06T06:42:28.9266761Z   set-safe-directory: true
2026-02-06T06:42:28.9267160Z ##[endgroup]
2026-02-06T06:42:29.0271254Z Syncing repository: aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:42:29.0273312Z ##[group]Getting Git version info
2026-02-06T06:42:29.0273907Z Working directory is '/home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production'
2026-02-06T06:42:29.0274604Z [command]/usr/bin/git version
2026-02-06T06:42:29.5547221Z git version 2.52.0
2026-02-06T06:42:29.5573265Z ##[endgroup]
2026-02-06T06:42:29.5600810Z Temporarily overriding HOME='/home/runner/work/_temp/1c845072-618f-428f-a9e7-633bbf72a8af' before making global git config changes
2026-02-06T06:42:29.5602350Z Adding repository directory to the temporary git global config as a safe directory
2026-02-06T06:42:29.5607808Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:42:29.5876469Z Deleting the contents of '/home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production'
2026-02-06T06:42:29.5880003Z ##[group]Initializing the repository
2026-02-06T06:42:29.5885488Z [command]/usr/bin/git init /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:42:29.8378073Z hint: Using 'master' as the name for the initial branch. This default branch name
2026-02-06T06:42:29.8378911Z hint: will change to "main" in Git 3.0. To configure the initial branch name
2026-02-06T06:42:29.8379388Z hint: to use in all of your new repositories, which will suppress this warning,
2026-02-06T06:42:29.8379749Z hint: call:
2026-02-06T06:42:29.8379926Z hint:
2026-02-06T06:42:29.8380208Z hint: 	git config --global init.defaultBranch <name>
2026-02-06T06:42:29.8380485Z hint:
2026-02-06T06:42:29.8380761Z hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
2026-02-06T06:42:29.8382067Z hint: 'development'. The just-created branch can be renamed via this command:
2026-02-06T06:42:29.8382409Z hint:
2026-02-06T06:42:29.8382618Z hint: 	git branch -m <name>
2026-02-06T06:42:29.8382822Z hint:
2026-02-06T06:42:29.8383131Z hint: Disable this message with "git config set advice.defaultBranchName false"
2026-02-06T06:42:29.8602686Z Initialized empty Git repository in /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production/.git/
2026-02-06T06:42:29.8616556Z [command]/usr/bin/git remote add origin https://github.com/aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:42:29.8900978Z ##[endgroup]
2026-02-06T06:42:29.8901465Z ##[group]Disabling automatic garbage collection
2026-02-06T06:42:29.8907461Z [command]/usr/bin/git config --local gc.auto 0
2026-02-06T06:42:29.8936385Z ##[endgroup]
2026-02-06T06:42:29.8936968Z ##[group]Setting up auth
2026-02-06T06:42:29.8944529Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-02-06T06:42:29.8971980Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-02-06T06:42:30.6110681Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-02-06T06:42:30.6146680Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-02-06T06:42:30.6350944Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
2026-02-06T06:42:30.6388206Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
2026-02-06T06:42:30.6583758Z [command]/usr/bin/git config --local http.https://github.com/.extraheader AUTHORIZATION: basic ***
2026-02-06T06:42:30.6616915Z ##[endgroup]
2026-02-06T06:42:30.6617622Z ##[group]Fetching the repository
2026-02-06T06:42:30.6627040Z [command]/usr/bin/git -c protocol.version=2 fetch --no-tags --prune --no-recurse-submodules --depth=1 origin +e12f3f9681c1287846369f61b494f8403d7cb1aa:refs/remotes/origin/main
2026-02-06T06:42:31.4397991Z From https://github.com/aaronshirley751/ibkr-trading-bot-production
2026-02-06T06:42:31.4402681Z  * [new ref]         e12f3f9681c1287846369f61b494f8403d7cb1aa -> origin/main
2026-02-06T06:42:31.4733791Z ##[endgroup]
2026-02-06T06:42:31.4734341Z ##[group]Determining the checkout info
2026-02-06T06:42:31.4735463Z ##[endgroup]
2026-02-06T06:42:31.4741481Z [command]/usr/bin/git sparse-checkout disable
2026-02-06T06:42:31.5042399Z [command]/usr/bin/git config --local --unset-all extensions.worktreeConfig
2026-02-06T06:42:31.5067986Z ##[group]Checking out the ref
2026-02-06T06:42:31.5073467Z [command]/usr/bin/git checkout --progress --force -B main refs/remotes/origin/main
2026-02-06T06:42:31.5382240Z Switched to a new branch 'main'
2026-02-06T06:42:31.5383922Z branch 'main' set up to track 'origin/main'.
2026-02-06T06:42:31.5391469Z ##[endgroup]
2026-02-06T06:42:31.5425049Z [command]/usr/bin/git log -1 --format=%H
2026-02-06T06:42:31.5444109Z e12f3f9681c1287846369f61b494f8403d7cb1aa
2026-02-06T06:42:31.5648360Z ##[group]Run actions/setup-python@v5
2026-02-06T06:42:31.5648635Z with:
2026-02-06T06:42:31.5648810Z   python-version: 3.12
2026-02-06T06:42:31.5649021Z   check-latest: false
2026-02-06T06:42:31.5649335Z   token: ***
2026-02-06T06:42:31.5649513Z   update-environment: true
2026-02-06T06:42:31.5649733Z   allow-prereleases: false
2026-02-06T06:42:31.5649970Z   freethreaded: false
2026-02-06T06:42:31.5650187Z ##[endgroup]
2026-02-06T06:42:31.7224797Z ##[group]Installed versions
2026-02-06T06:42:32.0042089Z Successfully set up CPython (3.12.12)
2026-02-06T06:42:32.0043002Z ##[endgroup]
2026-02-06T06:42:32.0170467Z ##[group]Run snok/install-poetry@v1
2026-02-06T06:42:32.0170713Z with:
2026-02-06T06:42:32.0170867Z   version: 2.3.2
2026-02-06T06:42:32.0171050Z   virtualenvs-create: true
2026-02-06T06:42:32.0171255Z   virtualenvs-in-project: true
2026-02-06T06:42:32.0171496Z   virtualenvs-path: {cache-dir}/virtualenvs
2026-02-06T06:42:32.0171894Z   installer-parallel: true
2026-02-06T06:42:32.0172101Z env:
2026-02-06T06:42:32.0172313Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0172711Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:42:32.0173080Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0173403Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0173731Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0174063Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:42:32.0174343Z ##[endgroup]
2026-02-06T06:42:32.0256138Z ##[group]Run $GITHUB_ACTION_PATH/main.sh
2026-02-06T06:42:32.0256462Z [36;1m$GITHUB_ACTION_PATH/main.sh[0m
2026-02-06T06:42:32.0508207Z shell: /usr/bin/bash --noprofile --norc -e -o pipefail {0}
2026-02-06T06:42:32.0508531Z env:
2026-02-06T06:42:32.0508772Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0509147Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:42:32.0509552Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0509879Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0510213Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:32.0510549Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:42:32.0510822Z   VERSION: 2.3.2
2026-02-06T06:42:32.0511006Z   VIRTUALENVS_CREATE: true
2026-02-06T06:42:32.0511205Z   VIRTUALENVS_IN_PROJECT: true
2026-02-06T06:42:32.0511446Z   VIRTUALENVS_PATH: {cache-dir}/virtualenvs
2026-02-06T06:42:32.0511963Z   INSTALLER_PARALLEL: true
2026-02-06T06:42:32.0512223Z   INSTALLATION_ARGUMENTS:
2026-02-06T06:42:32.0512550Z   POETRY_PLUGINS:
2026-02-06T06:42:32.0512779Z ##[endgroup]
2026-02-06T06:42:35.4107298Z
2026-02-06T06:42:35.4108266Z [33mSetting Poetry installation path as /home/runner/.local[0m
2026-02-06T06:42:35.4108540Z
2026-02-06T06:42:35.4108679Z [33mInstalling Poetry 👷[0m
2026-02-06T06:42:35.4108865Z
2026-02-06T06:42:49.8073488Z Retrieving Poetry metadata
2026-02-06T06:42:49.8073850Z
2026-02-06T06:42:49.8074073Z # Welcome to Poetry!
2026-02-06T06:42:49.8074297Z
2026-02-06T06:42:49.8074620Z This will download and install the latest version of Poetry,
2026-02-06T06:42:49.8075328Z a dependency and package manager for Python.
2026-02-06T06:42:49.8080723Z
2026-02-06T06:42:49.8081277Z It will add the `poetry` command to Poetry's bin directory, located at:
2026-02-06T06:42:49.8081883Z
2026-02-06T06:42:49.8082011Z /home/runner/.local/bin
2026-02-06T06:42:49.8082248Z
2026-02-06T06:42:49.8082593Z You can uninstall at any time by executing this script with the --uninstall option,
2026-02-06T06:42:49.8083168Z and these changes will be reverted.
2026-02-06T06:42:49.8083415Z
2026-02-06T06:42:49.8083534Z Installing Poetry (2.3.2)
2026-02-06T06:42:49.8083935Z Installing Poetry (2.3.2): Creating environment
2026-02-06T06:42:49.8084360Z Installing Poetry (2.3.2): Installing Poetry
2026-02-06T06:42:49.8085109Z Installing Poetry (2.3.2): Creating script
2026-02-06T06:42:49.8085469Z Installing Poetry (2.3.2): Done
2026-02-06T06:42:49.8085679Z
2026-02-06T06:42:49.8085821Z Poetry (2.3.2) is installed now. Great!
2026-02-06T06:42:49.8086055Z
2026-02-06T06:42:49.8086237Z You can test that everything is set up by executing:
2026-02-06T06:42:49.8086546Z
2026-02-06T06:42:49.8086651Z `poetry --version`
2026-02-06T06:42:49.8086881Z
2026-02-06T06:42:53.7220695Z
2026-02-06T06:42:53.7221529Z [33mInstallation completed. Configuring settings 🛠[0m
2026-02-06T06:42:53.7222040Z
2026-02-06T06:42:53.7222534Z [33mDone ✅[0m
2026-02-06T06:42:53.7222707Z
2026-02-06T06:42:53.7223789Z [33mIf you are creating a venv in your project, you can activate it by running 'source .venv/bin/activate'. If you're running this in an OS matrix, you can use 'source $VENV' instead, as an OS agnostic option[0m
2026-02-06T06:42:53.7937897Z ##[group]Run actions/cache@v4
2026-02-06T06:42:53.7938125Z with:
2026-02-06T06:42:53.7938301Z   path: .venv
2026-02-06T06:42:53.7938643Z   key: venv-Linux-443fe1c6fdf2e8b7fd4ad860fa59f3b8c699cbecd93c25cb52e82fa3f8c958b0
2026-02-06T06:42:53.7939040Z   enableCrossOsArchive: false
2026-02-06T06:42:53.7939258Z   fail-on-cache-miss: false
2026-02-06T06:42:53.7939453Z   lookup-only: false
2026-02-06T06:42:53.7939630Z   save-always: false
2026-02-06T06:42:53.7939800Z env:
2026-02-06T06:42:53.7940011Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:53.7940389Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:42:53.7940751Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:53.7941084Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:53.7941403Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:53.7942220Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:42:53.7942639Z   VENV: .venv/bin/activate
2026-02-06T06:42:53.7942911Z ##[endgroup]
2026-02-06T06:42:54.2610666Z Cache not found for input keys: venv-Linux-443fe1c6fdf2e8b7fd4ad860fa59f3b8c699cbecd93c25cb52e82fa3f8c958b0
2026-02-06T06:42:54.2668892Z ##[group]Run poetry install --no-interaction --no-root
2026-02-06T06:42:54.2669254Z [36;1mpoetry install --no-interaction --no-root[0m
2026-02-06T06:42:54.2689649Z shell: /usr/bin/bash -e {0}
2026-02-06T06:42:54.2689869Z env:
2026-02-06T06:42:54.2690116Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:54.2690499Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:42:54.2690881Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:54.2691207Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:54.2691536Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:42:54.2692134Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:42:54.2692422Z   VENV: .venv/bin/activate
2026-02-06T06:42:54.2692637Z ##[endgroup]
2026-02-06T06:42:54.6903169Z Creating virtualenv ibkr-trading-bot in /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production/.venv
2026-02-06T06:42:56.5360899Z Installing dependencies from lock file
2026-02-06T06:42:56.6917246Z
2026-02-06T06:42:56.6918046Z Package operations: 47 installs, 0 updates, 0 removals
2026-02-06T06:42:56.6918437Z
2026-02-06T06:42:56.6922291Z   - Installing aiohappyeyeballs (2.6.1)
2026-02-06T06:42:56.6929432Z   - Installing aiohttp (3.13.3)
2026-02-06T06:42:56.6933252Z   - Installing aiosignal (1.4.0)
2026-02-06T06:42:56.6950231Z   - Installing annotated-types (0.7.0)
2026-02-06T06:42:56.6974386Z   - Installing attrs (25.4.0)
2026-02-06T06:42:56.6988147Z   - Installing black (26.1.0)
2026-02-06T06:42:56.6998491Z   - Installing cfgv (3.5.0)
2026-02-06T06:42:56.7006671Z   - Installing click (8.3.1)
2026-02-06T06:42:56.9609874Z   - Installing coverage (7.13.3)
2026-02-06T06:42:56.9684401Z   - Installing distlib (0.4.0)
2026-02-06T06:42:57.0358805Z   - Installing eventkit (1.0.3)
2026-02-06T06:42:57.0502235Z   - Installing filelock (3.20.3)
2026-02-06T06:42:57.0655381Z   - Installing frozenlist (1.8.0)
2026-02-06T06:42:57.0966860Z   - Installing ib-insync (0.9.86)
2026-02-06T06:42:57.1413740Z   - Installing identify (2.6.16)
2026-02-06T06:42:57.1531955Z   - Installing idna (3.11)
2026-02-06T06:42:57.2086203Z   - Installing iniconfig (2.3.0)
2026-02-06T06:42:57.2129353Z   - Installing librt (0.7.8)
2026-02-06T06:42:57.2298609Z   - Installing multidict (6.7.1)
2026-02-06T06:42:57.2472637Z   - Installing mypy (1.19.1)
2026-02-06T06:42:57.2553918Z   - Installing mypy-extensions (1.1.0)
2026-02-06T06:42:57.3133656Z   - Installing nest-asyncio (1.6.0)
2026-02-06T06:42:57.3154962Z   - Installing nodeenv (1.10.0)
2026-02-06T06:42:57.3362334Z   - Installing numpy (2.4.2)
2026-02-06T06:42:57.3735722Z   - Installing packaging (26.0)
2026-02-06T06:42:57.3843497Z   - Installing pandas (3.0.0)
2026-02-06T06:42:57.3920216Z   - Installing pathspec (1.0.4)
2026-02-06T06:42:57.4327366Z   - Installing platformdirs (4.5.1)
2026-02-06T06:42:57.4871474Z   - Installing pluggy (1.6.0)
2026-02-06T06:42:57.5095341Z   - Installing pre-commit (4.5.1)
2026-02-06T06:42:57.5231229Z   - Installing propcache (0.4.1)
2026-02-06T06:42:57.5781683Z   - Installing pydantic (2.12.5)
2026-02-06T06:42:57.6929457Z   - Installing pydantic-core (2.41.5)
2026-02-06T06:42:57.8074347Z   - Installing pygments (2.19.2)
2026-02-06T06:42:57.8529946Z   - Installing pytest (9.0.2)
2026-02-06T06:42:57.8826572Z   - Installing pytest-asyncio (1.3.0)
2026-02-06T06:42:57.9463834Z   - Installing pytest-cov (7.0.0)
2026-02-06T06:42:58.0156528Z   - Installing python-dateutil (2.9.0.post0)
2026-02-06T06:42:58.0376999Z   - Installing python-dotenv (1.2.1)
2026-02-06T06:42:58.1396031Z   - Installing pytokens (0.4.1)
2026-02-06T06:42:58.1937819Z   - Installing pyyaml (6.0.3)
2026-02-06T06:42:58.2616411Z   - Installing ruff (0.15.0)
2026-02-06T06:42:58.2909351Z   - Installing six (1.17.0)
2026-02-06T06:42:58.3449430Z   - Installing typing-extensions (4.15.0)
2026-02-06T06:42:58.3806577Z   - Installing typing-inspection (0.4.2)
2026-02-06T06:42:58.4191969Z   - Installing virtualenv (20.36.1)
2026-02-06T06:42:58.4583003Z   - Installing yarl (1.22.0)
2026-02-06T06:43:00.2502940Z ##[group]Run poetry run ruff check src/ tests/
2026-02-06T06:43:00.2503321Z [36;1mpoetry run ruff check src/ tests/[0m
2026-02-06T06:43:00.2524148Z shell: /usr/bin/bash -e {0}
2026-02-06T06:43:00.2524375Z env:
2026-02-06T06:43:00.2524619Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.2525028Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:43:00.2525413Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.2525741Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.2526076Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.2526421Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:43:00.2526723Z   VENV: .venv/bin/activate
2026-02-06T06:43:00.2526920Z ##[endgroup]
2026-02-06T06:43:00.6878439Z All checks passed!
2026-02-06T06:43:00.6908950Z ##[group]Run poetry run black --check src/ tests/
2026-02-06T06:43:00.6909296Z [36;1mpoetry run black --check src/ tests/[0m
2026-02-06T06:43:00.6928576Z shell: /usr/bin/bash -e {0}
2026-02-06T06:43:00.6928796Z env:
2026-02-06T06:43:00.6929038Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.6929422Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:43:00.6929794Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.6930119Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.6930449Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:00.6930786Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:43:00.6931065Z   VENV: .venv/bin/activate
2026-02-06T06:43:00.6931421Z ##[endgroup]
2026-02-06T06:43:01.8875583Z All done! ✨ 🍰 ✨
2026-02-06T06:43:01.8875989Z 11 files would be left unchanged.
2026-02-06T06:43:01.9164601Z ##[group]Run poetry run mypy src/
2026-02-06T06:43:01.9164873Z [36;1mpoetry run mypy src/[0m
2026-02-06T06:43:01.9188393Z shell: /usr/bin/bash -e {0}
2026-02-06T06:43:01.9188629Z env:
2026-02-06T06:43:01.9188874Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:01.9189252Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:43:01.9190279Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:01.9190666Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:01.9191005Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:01.9191350Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:43:01.9191803Z   VENV: .venv/bin/activate
2026-02-06T06:43:01.9192062Z ##[endgroup]
2026-02-06T06:43:03.6993297Z Success: no issues found in 7 source files
2026-02-06T06:43:03.7061268Z ##[group]Run poetry run pytest tests/ --verbose
2026-02-06T06:43:03.7061780Z [36;1mpoetry run pytest tests/ --verbose[0m
2026-02-06T06:43:03.7062045Z [36;1mexit_code=$?[0m
2026-02-06T06:43:03.7062254Z [36;1mif [ $exit_code -eq 5 ]; then[0m
2026-02-06T06:43:03.7062485Z [36;1m  echo "No tests collected."[0m
2026-02-06T06:43:03.7062749Z [36;1m  exit 0[0m
2026-02-06T06:43:03.7062912Z [36;1mfi[0m
2026-02-06T06:43:03.7063076Z [36;1mexit $exit_code[0m
2026-02-06T06:43:03.7082522Z shell: /usr/bin/bash -e {0}
2026-02-06T06:43:03.7082748Z env:
2026-02-06T06:43:03.7083001Z   pythonLocation: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:03.7083389Z   PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib/pkgconfig
2026-02-06T06:43:03.7083761Z   Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:03.7084092Z   Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:03.7084495Z   Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.12.12/x64
2026-02-06T06:43:03.7084838Z   LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.12.12/x64/lib
2026-02-06T06:43:03.7085135Z   VENV: .venv/bin/activate
2026-02-06T06:43:03.7085324Z ##[endgroup]
2026-02-06T06:43:05.4711899Z ============================= test session starts ==============================
2026-02-06T06:43:05.4712917Z platform linux -- Python 3.12.12, pytest-9.0.2, pluggy-1.6.0 -- /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production/.venv/bin/python
2026-02-06T06:43:05.4713650Z cachedir: .pytest_cache
2026-02-06T06:43:05.4714073Z rootdir: /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:43:05.4714553Z configfile: pyproject.toml
2026-02-06T06:43:05.4714820Z plugins: cov-7.0.0, asyncio-1.3.0
2026-02-06T06:43:05.4715394Z asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
2026-02-06T06:43:05.5088650Z collecting ... collected 0 items
2026-02-06T06:43:05.5089032Z
2026-02-06T06:43:05.5089202Z ============================ no tests ran in 0.01s =============================
2026-02-06T06:43:05.5434691Z ##[error]Process completed with exit code 5.
2026-02-06T06:43:05.5515861Z Post job cleanup.
2026-02-06T06:43:05.6406008Z [command]/usr/bin/git version
2026-02-06T06:43:05.6442167Z git version 2.52.0
2026-02-06T06:43:05.6480270Z Temporarily overriding HOME='/home/runner/work/_temp/74140382-cf5c-4a86-b709-0fc00598a45e' before making global git config changes
2026-02-06T06:43:05.6481534Z Adding repository directory to the temporary git global config as a safe directory
2026-02-06T06:43:05.6495001Z [command]/usr/bin/git config --global --add safe.directory /home/runner/work/ibkr-trading-bot-production/ibkr-trading-bot-production
2026-02-06T06:43:05.6530024Z [command]/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
2026-02-06T06:43:05.6559608Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
2026-02-06T06:43:05.6976622Z [command]/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
2026-02-06T06:43:05.6998734Z http.https://github.com/.extraheader
2026-02-06T06:43:05.7009471Z [command]/usr/bin/git config --local --unset-all http.https://github.com/.extraheader
2026-02-06T06:43:05.7036747Z [command]/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
2026-02-06T06:43:05.7220304Z [command]/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
2026-02-06T06:43:05.7247938Z [command]/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
2026-02-06T06:43:05.7523768Z Cleaning up orphan processes
