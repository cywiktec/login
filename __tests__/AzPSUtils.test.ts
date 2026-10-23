import * as core from '@actions/core';
import * as exec from '@actions/exec';
import * as io from '@actions/io';
import { AzPSConstants, AzPSUtils } from '../src/PowerShell/AzPSUtils';

jest.mock('@actions/exec', () => ({ exec: jest.fn() }));
jest.mock('@actions/io', () => ({ which: jest.fn() }));

const mockedExec = exec.exec as jest.MockedFunction<typeof exec.exec>;
const mockedWhich = io.which as jest.MockedFunction<typeof io.which>;

describe('AzPSUtils', () => {
    const originalEnv = { ...process.env };

    beforeEach(() => {
        jest.clearAllMocks();
        mockedWhich.mockResolvedValue('/usr/bin/pwsh');
        jest.spyOn(core, 'debug').mockImplementation(() => {});
        jest.spyOn(core, 'warning').mockImplementation(() => {});
        jest.spyOn(core, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        process.env = { ...originalEnv };
        jest.restoreAllMocks();
    });

    test.each([
        ['Linux', AzPSConstants.DEFAULT_AZ_PATH_ON_LINUX],
        ['Windows', AzPSConstants.DEFAULT_AZ_PATH_ON_WINDOWS]
    ])('adds the default module path for %s', async (runner, path) => {
        process.env.RUNNER_OS = runner;
        process.env.PSModulePath = 'existing';

        await AzPSUtils.setPSModulePathForGitHubRunner();

        expect(process.env.PSModulePath).toBe(`${path}${require('path').delimiter}existing`);
    });

    test.each(['macOS', 'mystery'])('warns and skips module path updates for %s', async (runner) => {
        process.env.RUNNER_OS = runner;
        process.env.PSModulePath = 'existing';
        const warning = core.warning as jest.Mock;

        await AzPSUtils.setPSModulePathForGitHubRunner();

        expect(process.env.PSModulePath).toBe('existing');
        expect(warning).toHaveBeenCalledWith(expect.stringContaining(runner.toLowerCase()));
    });

    test('returns a successful PowerShell JSON result and merges provided environment values', async () => {
        process.env.EXISTING_VALUE = 'preserved';
        mockedExec.mockImplementation(async (_command, _args, options) => {
            options?.listeners?.stdout?.(Buffer.from('{"Success":true,"Result":"module-path"}'));
            return 0;
        });

        await expect(AzPSUtils.runPSFile(['-File', 'login.ps1'], { TOKEN: 'secret' })).resolves.toBe('module-path');

        expect(mockedWhich).toHaveBeenCalledWith('pwsh', true);
        expect(mockedExec.mock.calls[0][2]?.env).toMatchObject({
            EXISTING_VALUE: 'preserved',
            TOKEN: 'secret'
        });
    });

    test('rejects a PowerShell result reporting failure', async () => {
        mockedExec.mockImplementation(async (_command, _args, options) => {
            options?.listeners?.stdout?.(Buffer.from('{"Success":false,"Error":"bad credentials"}'));
            return 0;
        });

        await expect(AzPSUtils.runPSScript('script')).rejects.toThrow('Azure PowerShell login failed with error: bad credentials');
    });

    test('rejects PowerShell stderr even when the command emits success JSON', async () => {
        mockedExec.mockImplementation(async (_command, _args, options) => {
            options?.listeners?.stdout?.(Buffer.from('{"Success":true,"Result":"ok"}'));
            options?.listeners?.stderr?.(Buffer.from('PowerShell reported an error'));
            return 0;
        });

        await expect(AzPSUtils.runPSFile(['-File', 'login.ps1'])).rejects.toThrow('Azure PowerShell login failed with errors.');
        expect(core.error).toHaveBeenCalledWith('PowerShell reported an error');
    });

    test('rejects malformed PowerShell output', async () => {
        mockedExec.mockImplementation(async (_command, _args, options) => {
            options?.listeners?.stdout?.(Buffer.from('not-json'));
            return 0;
        });

        await expect(AzPSUtils.runPSFile(['-File', 'login.ps1'])).rejects.toThrow(SyntaxError);
    });
});
