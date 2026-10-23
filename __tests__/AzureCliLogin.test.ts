import * as core from '@actions/core';
import * as exec from '@actions/exec';
import * as io from '@actions/io';
import { AzureCliLogin } from '../src/Cli/AzureCliLogin';
import { LoginConfig } from '../src/common/LoginConfig';

jest.mock('@actions/exec', () => ({ exec: jest.fn() }));
jest.mock('@actions/io', () => ({ which: jest.fn() }));

const mockedExec = exec.exec as jest.MockedFunction<typeof exec.exec>;
const mockedWhich = io.which as jest.MockedFunction<typeof io.which>;

function config(overrides: Partial<LoginConfig> = {}): LoginConfig {
    return Object.assign(new LoginConfig(), {
        environment: 'azurecloud',
        authType: LoginConfig.AUTH_TYPE_SERVICE_PRINCIPAL,
        servicePrincipalId: 'client-id',
        servicePrincipalSecret: 'client-secret',
        tenantId: 'tenant-id',
        subscriptionId: 'subscription-id',
        allowNoSubscriptionsLogin: false,
        ...overrides
    });
}

function provideVersion(version: string): void {
    mockedExec.mockImplementation(async (_command, args, options) => {
        if (args[0] === 'version') {
            options?.listeners?.stdout?.(Buffer.from(JSON.stringify({ 'azure-cli': version })));
        }
        return 0;
    });
}

describe('AzureCliLogin', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        mockedWhich.mockResolvedValue('/usr/bin/az');
        jest.spyOn(core, 'info').mockImplementation(() => {});
        jest.spyOn(core, 'debug').mockImplementation(() => {});
        jest.spyOn(core, 'warning').mockImplementation(() => {});
        jest.spyOn(core, 'error').mockImplementation(() => {});
    });

    afterEach(() => jest.restoreAllMocks());

    test('logs in with a service principal secret and selects the subscription', async () => {
        provideVersion('2.70.0');
        const login = new AzureCliLogin(config());

        await login.login();

        const calls = mockedExec.mock.calls.map(([, args]) => args);
        expect(calls[0]).toEqual(['version']);
        expect(calls[1]).toEqual(['cloud', 'set', '-n', 'azurecloud']);
        expect(calls[2]).toEqual(expect.arrayContaining([
            'login', '--service-principal', '--username', 'client-id', '--tenant', 'tenant-id'
        ]));
        expect(calls[3]).toEqual(['account', 'set', '--subscription', 'subscription-id']);
        expect(mockedWhich).toHaveBeenCalledWith('az', true);
    });

    test('uses a federated token for a service principal without a secret', async () => {
        provideVersion('2.70.0');
        const loginConfig = config({ servicePrincipalSecret: null, federatedToken: 'token' });
        jest.spyOn(loginConfig, 'getFederatedToken').mockImplementation(async () => {});

        await new AzureCliLogin(loginConfig).login();

        expect(mockedExec.mock.calls[2][1]).toEqual(expect.arrayContaining(['--federated-token', 'token']));
        expect(loginConfig.getFederatedToken).toHaveBeenCalled();
    });

    test.each([
        ['2.68.0', '--username'],
        ['2.69.0', '--client-id']
    ])('selects the managed identity flag for Azure CLI %s', async (version, expectedFlag) => {
        provideVersion(version);

        await new AzureCliLogin(config({
            authType: LoginConfig.AUTH_TYPE_IDENTITY,
            servicePrincipalSecret: null
        })).login();

        expect(mockedExec.mock.calls[2][1]).toEqual(expect.arrayContaining([expectedFlag, 'client-id']));
    });

    test('uses system-assigned managed identity without a client ID', async () => {
        provideVersion('2.70.0');
        await new AzureCliLogin(config({
            authType: LoginConfig.AUTH_TYPE_IDENTITY,
            servicePrincipalId: '',
            servicePrincipalSecret: null,
            subscriptionId: ''
        })).login();

        expect(mockedExec.mock.calls[2][1]).toEqual(['login', '--identity']);
        expect(mockedExec).toHaveBeenCalledTimes(3);
    });

    test('allows sign-in without a subscription when configured', async () => {
        provideVersion('2.70.0');
        await new AzureCliLogin(config({
            allowNoSubscriptionsLogin: true,
            subscriptionId: ''
        })).login();

        expect(mockedExec.mock.calls[2][1]).toContain('--allow-no-subscriptions');
        expect(mockedExec).toHaveBeenCalledTimes(3);
    });

    test('registers Azure Stack and ignores a failure to unregister an unknown cloud', async () => {
        provideVersion('2.70.0');
        mockedExec.mockImplementation(async (_command, args, options) => {
            if (args[0] === 'version') {
                options?.listeners?.stdout?.(Buffer.from('{"azure-cli":"2.70.0"}'));
            }
            if (args[0] === 'cloud' && args[1] === 'unregister') {
                throw new Error('cloud is not registered');
            }
            return 0;
        });

        await new AzureCliLogin(config({
            environment: 'azurestack',
            resourceManagerEndpointUrl: 'https://management.local/'
        })).login();

        const registerCall = mockedExec.mock.calls.find(([, args]) => args[1] === 'register');
        expect(registerCall?.[1]).toEqual(expect.arrayContaining([
            '--endpoint-resource-manager', 'https://management.local/',
            '--suffix-keyvault-dns', '.local',
            '--suffix-storage-endpoint', 'local',
            '--profile', '2019-03-01-hybrid'
        ]));
        expect(core.info).toHaveBeenCalledWith(expect.stringContaining('Ignore cloud not registered error'));
    });

    test('requires an ARM endpoint for Azure Stack', async () => {
        provideVersion('2.70.0');
        await expect(new AzureCliLogin(config({ environment: 'azurestack' })).login())
            .rejects.toThrow('resourceManagerEndpointUrl is a required parameter');
        expect(mockedExec).toHaveBeenCalledTimes(1);
    });

    test('reports a cloud registration failure and rethrows it', async () => {
        provideVersion('2.70.0');
        const failure = new Error('registration failed');
        mockedExec.mockImplementation(async (_command, args, options) => {
            if (args[0] === 'version') {
                options?.listeners?.stdout?.(Buffer.from('{"azure-cli":"2.70.0"}'));
            }
            if (args[1] === 'register') {
                throw failure;
            }
            return 0;
        });

        await expect(new AzureCliLogin(config({
            environment: 'azurestack',
            resourceManagerEndpointUrl: 'https://management.local'
        })).login()).rejects.toBe(failure);
        expect(core.error).toHaveBeenCalledWith('Error while trying to register cloud "azurestack"');
    });

    test('warns and falls back to the legacy identity option for malformed CLI version output', async () => {
        mockedExec.mockImplementation(async (_command, args, options) => {
            if (args[0] === 'version') {
                options?.listeners?.stdout?.(Buffer.from('not-json'));
            }
            return 0;
        });

        await new AzureCliLogin(config({
            authType: LoginConfig.AUTH_TYPE_IDENTITY,
            servicePrincipalSecret: null
        })).login();

        expect(core.warning).toHaveBeenCalledWith('Failed to parse Azure CLI version.');
        expect(core.warning).toHaveBeenCalledWith(expect.stringContaining('Assuming the version is less than 2.69.0'));
        expect(mockedExec.mock.calls[2][1]).toContain('--username');
    });

    test('writes non-warning CLI stderr to the action error log', async () => {
        provideVersion('2.70.0');
        const login = new AzureCliLogin(config());
        login.azPath = '/usr/bin/az';
        await login.executeAzCliCommand(['account', 'show'], true, {
            listeners: { stderr: (data: Buffer) => core.error(data.toString()) }
        });

        const options = mockedExec.mock.calls[0][2];
        options?.listeners?.stderr?.(Buffer.from('WARNING: ignored'));
        options?.listeners?.stderr?.(Buffer.from('ERROR: failed'));
        expect(core.error).toHaveBeenCalledWith('ERROR: failed');
        expect(options?.silent).toBe(true);
    });
});
