import * as core from '@actions/core';
import { LoginConfig } from '../src/common/LoginConfig';

describe('LoginConfig federated token retrieval', () => {
    afterEach(() => jest.restoreAllMocks());

    function token(payload: Record<string, unknown>): string {
        return `header.${Buffer.from(JSON.stringify(payload)).toString('base64')}.signature`;
    }

    test('retrieves, masks, and reports required federated token claims', async () => {
        const claims = {
            iss: 'https://issuer.example',
            sub: 'subject',
            aud: 'audience',
            job_workflow_ref: 'owner/repo/.github/workflows/test.yml@main'
        };
        const setSecret = jest.spyOn(core, 'setSecret').mockImplementation(() => {});
        const getIDToken = jest.spyOn(core, 'getIDToken').mockResolvedValue(token(claims));
        const info = jest.spyOn(core, 'info').mockImplementation(() => {});
        const loginConfig = Object.assign(new LoginConfig(), { audience: 'expected-audience' });

        await loginConfig.getFederatedToken();

        expect(getIDToken).toHaveBeenCalledWith('expected-audience');
        expect(loginConfig.federatedToken).toBe(token(claims));
        expect(setSecret).toHaveBeenCalledWith(token(claims));
        expect(info).toHaveBeenCalledWith(expect.stringContaining('issuer - https://issuer.example'));
    });

    test('warns rather than failing when token claims are malformed', async () => {
        jest.spyOn(core, 'getIDToken').mockResolvedValue('not-a-jwt');
        const warning = jest.spyOn(core, 'warning').mockImplementation(() => {});
        const loginConfig = new LoginConfig();

        await expect(loginConfig.getFederatedToken()).resolves.toBeUndefined();
        expect(warning).toHaveBeenCalledWith(expect.stringContaining('Failed to parse the federated token'));
    });

    test.each(['iss', 'sub', 'aud', 'job_workflow_ref'])('warns when required claim %s is absent', async (claim) => {
        const claims = { iss: 'issuer', sub: 'subject', aud: 'audience', job_workflow_ref: 'workflow' };
        delete (claims as Record<string, string>)[claim];
        jest.spyOn(core, 'getIDToken').mockResolvedValue(token(claims));
        const warning = jest.spyOn(core, 'warning').mockImplementation(() => {});

        await new LoginConfig().getFederatedToken();

        expect(warning).toHaveBeenCalledWith(expect.stringContaining(`claim '${claim}' is missing`));
    });

    test('logs and rethrows an ID token retrieval failure', async () => {
        const failure = new Error('permission denied');
        jest.spyOn(core, 'getIDToken').mockRejectedValue(failure);
        const error = jest.spyOn(core, 'error').mockImplementation(() => {});

        await expect(new LoginConfig().getFederatedToken()).rejects.toBe(failure);
        expect(error).toHaveBeenCalledWith(expect.stringContaining('Failed to fetch federated token'));
    });
});
