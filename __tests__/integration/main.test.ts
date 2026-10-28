describe('main login orchestration', () => {
    async function runMain(options: {
        preCleanup?: boolean;
        enablePowerShell?: boolean;
        configError?: Error;
        cliError?: Error;
    } = {}) {
        jest.resetModules();
        const calls: string[] = [];
        const core = {
            getInput: jest.fn((name: string) => name === 'enable-AzPSSession' && options.enablePowerShell ? 'true' : ''),
            setFailed: jest.fn(),
            debug: jest.fn()
        };
        const utils = {
            setUserAgent: jest.fn(() => calls.push('user-agent')),
            cleanupAzCLIAccounts: jest.fn(async () => { calls.push('cleanup-cli'); }),
            cleanupAzPSAccounts: jest.fn(async () => { calls.push('cleanup-ps'); })
        };
        class MockLoginConfig {
            enableAzPSSession = options.enablePowerShell ?? false;
            initialize = jest.fn(async () => {
                calls.push('initialize');
                if (options.configError) { throw options.configError; }
            });
            validate = jest.fn(async () => { calls.push('validate'); });
        }
        class MockCliLogin {
            constructor(_config: unknown) {}
            login = jest.fn(async () => {
                calls.push('cli-login');
                if (options.cliError) { throw options.cliError; }
            });
        }
        class MockPsLogin {
            constructor(_config: unknown) {}
            login = jest.fn(async () => { calls.push('ps-login'); });
        }

        jest.doMock('@actions/core', () => core);
        jest.doMock('../../src/common/Utils', () => utils);
        jest.doMock('../../src/common/LoginConfig', () => ({ LoginConfig: MockLoginConfig }));
        jest.doMock('../../src/Cli/AzureCliLogin', () => ({ AzureCliLogin: MockCliLogin }));
        jest.doMock('../../src/PowerShell/AzPSLogin', () => ({ AzPSLogin: MockPsLogin }));
        process.env.AZURE_LOGIN_PRE_CLEANUP = options.preCleanup ? 'true' : 'false';

        require('../../src/main');
        await new Promise(resolve => setImmediate(resolve));
        delete process.env.AZURE_LOGIN_PRE_CLEANUP;
        return { calls, core, utils };
    }

    afterEach(() => jest.resetModules());

    test('initializes and validates before CLI login and omits PowerShell when disabled', async () => {
        const { calls, core } = await runMain();
        expect(calls).toEqual(['user-agent', 'initialize', 'validate', 'cli-login']);
        expect(core.setFailed).not.toHaveBeenCalled();
    });

    test('runs pre-cleanup and logs into CLI and PowerShell in sequence', async () => {
        const { calls, utils } = await runMain({ preCleanup: true, enablePowerShell: true });
        expect(calls).toEqual([
            'user-agent', 'cleanup-cli', 'cleanup-ps', 'initialize', 'validate', 'cli-login', 'ps-login'
        ]);
        expect(utils.cleanupAzCLIAccounts).toHaveBeenCalledTimes(1);
        expect(utils.cleanupAzPSAccounts).toHaveBeenCalledTimes(1);
    });

    test('reports configuration and CLI failures and skips later login steps', async () => {
        const configFailure = new Error('invalid inputs');
        const configResult = await runMain({ configError: configFailure, enablePowerShell: true });
        expect(configResult.core.setFailed).toHaveBeenCalledWith(expect.stringContaining('invalid inputs'));
        expect(configResult.calls).not.toContain('cli-login');

        jest.resetModules();
        const cliFailure = new Error('CLI unavailable');
        const cliResult = await runMain({ cliError: cliFailure, enablePowerShell: true });
        expect(cliResult.core.setFailed).toHaveBeenCalledWith(expect.stringContaining('CLI unavailable'));
        expect(cliResult.calls).not.toContain('ps-login');
    });
});
