# Tests for the lambda functions

Testing of Lambda functions in this directory is provided with two mechanisms:

* Language-native testing suites (e.g. [Jest](https://jestjs.io/))
* Bash scripts and runner stubs 

The native test suites are advised for general development and validation of the lambda function, however, the bash scripts can be helpful when porting the functions to other languages (such as TypeScript to Python). Once ported, additional language-native test suites (e.g. [unittest](https://docs.python.org/3/library/unittest.html)) should be used to fully test the functions. 

### Sample test event

All the Lambda functions have at least one sample event in the `lambdas/<function-name>/events` directory. Both the native suites and the bash suites use these samples as starting points for test cases.

## Running the native test suites (TypeScript)

**NB:** As of Jest v28, a breaking change was introduced on test construction. For convenience, v27 is recommended and included in the `package.json` files.

1. Change to the 'src' directory of the desired lambda function, `call-play-recording` for example.
2. Set `nvm` to use the node version that will be targetted for deployment, e.g. 'v14'
3. A `package.json` file is provided in the `src` directory to provide test scripts as well as to separate the packages needed for testing from those needed by the CDK project itself. **Install packages in this directory.** Likewise, a `jest.config.ts` file is also provided in the `src` directories.

**While packages should be installed from the `src` directory, they are incremental to those installed from the parent lambda directory. A clean and install from the parent is recommended before starting a test session.** 
4. Run tests.
5. Verify pass/fail of tests

```bash
# from the lambdas directory
cd call-play-recording
# start clean
yarn clean
yarn install

# switch to src directory and install additional packages
cd src

nvm use v14
node -v >.nvmrc

yarn install

yarn test
```

### Options, Tips, and Notes
* Tests can be run in a 'watch' mode with the command `yarn test:watch` which will continually run tests as code changes.
* TypeScript code is being tested natively and need not be transpiled prior to testing. That is, the test framework runs the transpilation transparently. Therefore, if you have remaining `js` files in the `src` directory, they may interfere with the Jest suite. **Delete transpilied `.js` files from this directory before running Jest.**  The clean script (`yarn clean`) will handle this.
* Using the [Visual Studio Code](https://code.visualstudio.com/) IDE can be helpful to set breakpoints in both the tests and the lambda function for testing. There are also "Test Explorer" plugins for graphical navigation of tests and status.
  - The current Jest explorer plugin for VS Code does not pick up the tests from this sub-directory.
  - Running the tests from the command line (`yarn test`) is recommended.
  - The VS Code debugger must first be 'activated' by opening the package.json file, which will overlay a 'Debug' icon above the `scripts` property.  Click this icon, select 'test' and debug the code. Subsequent invocations of `yarn test` from the command line will automatically attach the debugger.
* Inspect the coverage provided by the tests. Open the coverage report from `coverage/lcov-report/index.html` in a browser. This report is 'live' in that as you re-run the tests, the report is updated, but you will need to refresh the browser. The report is interactive and allows exploration of what code has been tested or missed. Test cases can be added as needed to improve coverage.
* Single tests can be run by using the `-t <susbstring>` option to `yarn test`.  Tests with descriptions matching the substring will be run.

## Running bash scripts with a lambda runner

A simple test runner to call the lambda function from a command line is provided in `src/test/lambda-runner.js`.  Note that this is a JavaScript runner and requires the TypeScript index.ts to be transpiled. The bash runner script will handle this. However, be sure to **delete the transpilied .js file** before running the Jest suite.

The bash runner uses a combination of schema validation and content inspection to validate the lambda returns. As such some tools need to be installed: [ajv](https://ajv.js.org/) and [jq](https://stedolan.github.io/jq/). 

To install on Debian-like Linux OS's

```bash
sudo apt install jq
npm install -g ajv-cli
```

Test suites are organized into `cases` under the `test` directory. Each case contains a bash script and may contain additional event samples or validation schemas.

To run the full suite:

```bash
# from a lambda function src dir -- e.g. lambdas/call-play-recording/src
cd test

# run the <function-name>.bash script
./call-play-recording-test.bash 
```

This script will
* transpile the function index.ts
* run the scripts in each of the cases

To troubleshoot individual case, change to the case directory and run the `.bash` script in that directory. For example,

```bash
cd cases/new-call 
./new-call.bash 
```

**Coverage analysis and debugging** is not supported from the bash scripts.


## Python dependencies

* jsonschema

Install from a lambda function's `src` directory with

```bash
pip3 install -r requirements.txt
```

## Python Notes

Debugging in VSCode:
- open a new window focused on the `src` dir
- disable the JEST plugin to get test exploration in sidebar
