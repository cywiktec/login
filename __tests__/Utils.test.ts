import * as core from '@actions/core';
import * as exec from '@actions/exec';
import * as io from '@actions/io';
import { cleanupAzCLIAccounts, cleanupAzPSAccounts, setUserAgent } from '../src/common/Utils';
import { AzPSUtils } from '../src/PowerShell/AzPSUtils';

jest.mock('@actions/exec', () => ({ exec: jest.fn() }));
jest.mock('@actions/io', () => ({ which: jest.fn() }));

const mockedExec = exec.exec as jest.MockedFunction<typeof exec.exec>;
const mockedWhich = io.which as jest.MockedFunction<typeof io.which>;

describe('common utilities', () => {
    const originalEnv = { ...process.env };

    beforeEach(() => {
        jest.clearAllMocks();
        process.env.GITHUB_REPOSITORY = 'owner/repo';
        process.env.GITHUB_ACTION_REF = 'owner/action@v1';
        process.env.RUNNER_ENVIRONMENT = 'github-hosted';
        process.env.GITHUB_RUN_ID = '42';
        delete process.env.AZURE_HTTP_USER_AGENT;
        delete process.env.AZUREPS_HOST_ENVIRONMENT;
        mockedWhich.mockResolvedValue('/usr/bin/az');
        jest.spyOn(core, 'info').mockImplementation(() => {});
        jest.spyOn(core, 'debug').mockImplementation(() => {});
    });

    afterEach(() => {
        process.env = { ...originalEnv };
        jest.restoreAllMocks();
    });

    test('sets and appends Azure user-agent environment values', () => {
        setUserAgent();
        expect(process.env.AZURE_HTTP_USER_AGENT).toContain('GITHUBACTIONS/AzureLogin@owner/action@v1_');
        expect(process.env.AZUREPS_HOST_ENVIRONMENT).toBe(process.env.AZURE_HTTP_USER_AGENT);

        process.env.AZURE_HTTP_USER_AGENT = 'existing-cli';
        process.env.AZUREPS_HOST_ENVIRONMENT = 'existing-ps';
        setUserAgent();
        expect(process.env.AZURE_HTTP_USER_AGENT).toMatch(/^existing-cli GITHUBACTIONS/);
        expect(process.env.AZUREPS_HOST_ENVIRONMENT).toMatch(/^existing-ps GITHUBACTIONS/);
    });

    test('clears CLI accounts using the located executable', async () => {
        await cleanupAzCLIAccounts();
        expect(mockedWhich).toHaveBeenCalledWith('az', true);
        expect(mockedExec).toHaveBeenCalledWith('"/usr/bin/az"', ['account', 'clear']);
    });

    test('clears PowerShell accounts after importing Az.Accounts', async () => {
        mockedWhich.mockResolvedValue('/usr/bin/pwsh');
        const setPath = jest.spyOn(AzPSUtils, 'setPSModulePathForGitHubRunner').mockResolvedValue();
        const importModule = jest.spyOn(AzPSUtils, 'importLatestAzAccounts').mockResolvedValue();

        await cleanupAzPSAccounts();

        expect(setPath).toHaveBeenCalled();
        expect(importModule).toHaveBeenCalled();
        expect(mockedExec).toHaveBeenNthCalledWith(1, '"/usr/bin/pwsh"', ['-Command', 'Clear-AzContext', '-Scope', 'Process']);
        expect(mockedExec).toHaveBeenNthCalledWith(2, '"/usr/bin/pwsh"', [
            '-Command', 'Clear-AzContext', '-Scope', 'CurrentUser', '-Force', '-ErrorAction', 'SilentlyContinue'
        ]);
    });
});
