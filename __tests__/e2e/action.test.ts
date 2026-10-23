import * as path from 'path';

describe('action E2E simulation', () => {
    const inputKeys = [
        'INPUT_ENVIRONMENT',
        'INPUT_ENABLE-AZPSSESSION',
        'INPUT_ALLOW-NO-SUBSCRIPTIONS',
        'INPUT_AUTH-TYPE',
        'INPUT_CREDS',
        'INPUT_MASK-CLIENT-ID'
    ];

    beforeEach(() => {
        jest.resetModules();
        process.env.RUNNER_OS = 'Linux';
        process.env.GITHUB_REPOSITORY = 'owner/repo';
        process.env.GITHUB_ACTION_REF = 'owner/action@v1';
        process.env.RUNNER_ENVIRONMENT = 'github-hosted';
        process.env.GITHUB_RUN_ID = '42';
        process.env.INPUT_ENVIRONMENT = 'azurecloud';
        process.env['INPUT_ENABLE-AZPSSESSION'] = 'true';
        process.env['INPUT_ALLOW-NO-SUBSCRIPTIONS'] = 'false';
        process.env['INPUT_AUTH-TYPE'] = 'SERVICE_PRINCIPAL';
        process.env.INPUT_CREDS = JSON.stringify({
            clientId: 'client-id',
            clientSecret: 'client-secret',
            tenantId: 'tenant-id',
            subscriptionId: 'subscription-id'
        });
        process.env['INPUT_MASK-CLIENT-ID'] = 'false';
    });

    afterEach(() => {
        inputKeys.forEach(key => delete process.env[key]);
        delete process.env.RUNNER_OS;
        jest.resetModules();
    });

    test('loads action inputs and runs CLI and PowerShell login without external Azure services', async () => {
        const commands: Array<{ command: string; args: string[] }> = [];
        jest.doMock('@actions/io', () => ({
            which: jest.fn(async (name: string) => name === 'az' ? '/fake/az' : '/fake/pwsh')
        }));
        jest.doMock('@actions/exec', () => ({
            exec: jest.fn(async (command: string, args: string[], options: any = {}) => {
                commands.push({ command, args });
                if (command === '"/fake/az"' && args[0] === 'version') {
                    options.listeners?.stdout(Buffer.from('{"azure-cli":"2.70.0"}'));
                } else if (command === '"/fake/pwsh"') {
                    options.listeners?.stdout(Buffer.from('{"Success":true,"Result":"module"}'));
                }
                return 0;
            })
        }));

        const core = require('@actions/core');
        const setFailed = jest.spyOn(core, 'setFailed').mockImplementation(() => {});
        require('../../src/main');
        await new Promise(resolve => setTimeout(resolve, 0));

        expect(setFailed).not.toHaveBeenCalled();
        expect(commands.some(({ command, args }) => command === '"/fake/az"' && args[0] === 'login')).toBe(true);
        expect(commands.some(({ command, args }) => command === '"/fake/pwsh"' && args.includes('-File'))).toBe(true);
        expect(commands.some(({ command, args }) => command === '"/fake/pwsh"' && args.includes('-Command'))).toBe(true);
        expect(path.isAbsolute(require('../../src/PowerShell/AzPSScriptBuilder').default.getScriptPath())).toBe(true);
    });
});
