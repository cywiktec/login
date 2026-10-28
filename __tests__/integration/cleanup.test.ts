describe('cleanup recovery orchestration', () => {
    async function runCleanup(enablePowerShell: boolean, failure?: Error) {
        jest.resetModules();
        const core = {
            getInput: jest.fn(() => enablePowerShell ? 'true' : ''),
            warning: jest.fn(),
            debug: jest.fn()
        };
        const utils = {
            setUserAgent: jest.fn(),
            cleanupAzCLIAccounts: jest.fn(async () => {
                if (failure) { throw failure; }
            }),
            cleanupAzPSAccounts: jest.fn(async () => {})
        };
        jest.doMock('@actions/core', () => core);
        jest.doMock('../../src/common/Utils', () => utils);

        require('../../src/cleanup');
        await new Promise(resolve => setImmediate(resolve));
        return { core, utils };
    }

    afterEach(() => jest.resetModules());

    test('cleans only CLI accounts when PowerShell sessions are disabled', async () => {
        const { utils } = await runCleanup(false);
        expect(utils.cleanupAzCLIAccounts).toHaveBeenCalledTimes(1);
        expect(utils.cleanupAzPSAccounts).not.toHaveBeenCalled();
    });

    test('cleans both CLI and PowerShell accounts when enabled', async () => {
        const { utils } = await runCleanup(true);
        expect(utils.cleanupAzCLIAccounts).toHaveBeenCalledTimes(1);
        expect(utils.cleanupAzPSAccounts).toHaveBeenCalledTimes(1);
    });

    test('recovers from CLI cleanup errors and emits a warning', async () => {
        const failure = new Error('cache failure');
        const { core } = await runCleanup(true, failure);
        expect(core.warning).toHaveBeenCalledWith(expect.stringContaining('Cleanup will be skipped'));
        expect(core.debug).toHaveBeenCalledWith(failure.stack);
    });
});
