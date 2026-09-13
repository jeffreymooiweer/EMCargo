/** Updates survive route changes and process restarts. These tests exercise the
 * observed server states, preserving settings, and the setup gate rather than
 * snapshotting presentation or assuming a working Docker socket. */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from '../api/client';
import UpdatePanel from './UpdatePanel';

const { success, translate } = vi.hoisted(() => ({ success: vi.fn(), translate: (key: string, params?: Record<string, unknown>) => params?.error ? `${key}: ${params.error}` : key }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: translate }) }));
vi.mock('../toast/ToastProvider', () => ({ useToast: () => ({ success }) }));
vi.mock('../api/client', () => ({ api: {
  updateCapability: vi.fn(), updateStatus: vi.fn(), updateState: vi.fn(), instanceSettings: vi.fn(),
  updateCheckNow: vi.fn(), updateApply: vi.fn(), saveInstanceSettings: vi.fn(),
} }));
const ability = { available: true, apply_enabled: true, socket: true, container: 'local', image: 'emcargo:2.1.1', reason: null };
const release = { enabled: true, reachable: true, current: '2.1.1', latest: '2.2.0', update_available: true };
const instance = { update_check_enabled: true, organisation_name: 'Example' };
const reload = vi.fn();
async function setup() {
  let view!: ReturnType<typeof render>;
  await act(async () => { view = render(<UpdatePanel />); });
  return view;
}
beforeEach(() => {
  vi.useFakeTimers(); vi.clearAllMocks();
  vi.stubGlobal('location', { reload });
  vi.mocked(api.updateCapability).mockResolvedValue(ability);
  vi.mocked(api.updateStatus).mockResolvedValue(release);
  vi.mocked(api.updateCheckNow).mockResolvedValue(release);
  vi.mocked(api.updateState).mockResolvedValue({ current: '2.1.1', state: null });
  vi.mocked(api.instanceSettings).mockResolvedValue(instance as any);
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

/** Since v2.8.0 administrators reported an endless refresh after updating.
 * The helper can still report an active phase after the target is serving
 * requests. Each new page must recognise that version instead of resuming
 * the same observer and reloading itself again 1.5 seconds later. */
it.each(['pulling', 'handed_over', 'stopping'] as const)('does not resume %s for the version already running, including after a refresh', async (phase) => {
  vi.mocked(api.updateStatus).mockResolvedValue({ ...release, current: '2.2.0', update_available: false });
  vi.mocked(api.updateState).mockResolvedValue({ current: '2.2.0', state: {
    phase, ...(phase === 'stopping' ? { to_image: 'ghcr.io/jeffreymooiweer/emcargo:2.2.0' } : { to: '2.2.0' }),
  } });
  for (let visit = 0; visit < 3; visit += 1) {
    const view = await setup();
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(reload).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'settings.updateCheckNow' })).toBeEnabled();
    view.unmount();
  }
  expect(api.updateState).toHaveBeenCalledTimes(3);
});

it('keeps an unreachable release check distinct from an up-to-date installation', async () => {
  vi.mocked(api.updateStatus).mockResolvedValue({ enabled: true, reachable: false, current: '2.1.1' });
  await setup();
  expect(screen.getByRole('status')).toHaveTextContent('settings.updateUnreachable');
  expect(screen.queryByText('settings.updateUpToDate')).not.toBeInTheDocument();
  await act(async () => fireEvent.click(screen.getByRole('button', { name: 'settings.updateCheckNow' })));
  expect(screen.getByRole('button', { name: 'settings.updateApplyNow' })).toBeEnabled();
});

it('keeps unavailable updates disabled without showing Docker setup instructions', async () => {
  vi.mocked(api.updateCapability).mockResolvedValue({ ...ability, available: false, socket: false, reason: 'no_socket' });
  await setup();
  expect(screen.getByRole('button', { name: 'settings.updateApplyNow' })).toBeDisabled();
  expect(screen.getByText('settings.updateReasonNoSocket')).toBeInTheDocument();
  expect(screen.queryByText('updates.setup')).not.toBeInTheDocument();
  expect(screen.queryByText(/docker\.sock|UPDATE_APPLY_ENABLED/)).not.toBeInTheDocument();
  expect(api.updateApply).not.toHaveBeenCalled();
});

it.each(['native', 'kubernetes'] as const)('preserves the update command for %s installations', async (method) => {
  vi.mocked(api.updateCapability).mockResolvedValue({ ...ability, available: false, install_method: method, reason: method });
  await setup();
  expect(screen.getByRole('button', { name: 'settings.updateApplyNow' })).toBeDisabled();
  expect(screen.getByText('updates.setup')).toBeInTheDocument();
  expect(screen.getByText(method === 'native'
    ? 'sudo /opt/emcargo/current/deploy/native/update.sh'
    : 'kubectl -n emcargo set image deployment/emcargo emcargo=ghcr.io/jeffreymooiweer/emcargo:2.2.0')).toBeInTheDocument();
});

it('changes only the update switch against the latest organisation settings', async () => {
  await setup();
  const latest = { ...instance, organisation_name: 'New name', external_url: 'https://example.invalid' };
  vi.mocked(api.instanceSettings).mockResolvedValue(latest as any);
  vi.mocked(api.saveInstanceSettings).mockResolvedValue({ ...latest, update_check_enabled: false } as any);
  await act(async () => fireEvent.click(screen.getByRole('switch')));
  expect(api.saveInstanceSettings).toHaveBeenCalledWith({ ...latest, update_check_enabled: false });
  expect(screen.getByRole('button', { name: 'settings.updateCheckNow' })).toBeDisabled();
});

it('resumes an active update and stops observing when the administrator leaves', async () => {
  vi.mocked(api.updateState).mockResolvedValue({ current: '2.1.1', state: { phase: 'handed_over', to: '2.2.0' } });
  const view = await setup();
  expect(screen.getByRole('status')).toHaveTextContent('settings.updatePhaseRestarting');
  await act(async () => { await vi.advanceTimersByTimeAsync(1600); });
  expect(api.updateState).toHaveBeenCalledTimes(2);
  view.unmount();
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(api.updateState).toHaveBeenCalledTimes(2);
});

/** A real restart still needs one reload to load the new assets. The helper
 * may not have finished, or another browser on an older server may have
 * consumed completion. Neither can restart the loop after that reload. */
it.each(['stopping', 'done', null] as const)('reloads once across downtime with %s progress, then remains usable', async (phase) => {
  const completed = { current: '2.2.0', state: phase ? {
    phase, to_image: 'ghcr.io/jeffreymooiweer/emcargo:2.2.0',
  } : null };
  vi.mocked(api.updateState)
    .mockResolvedValueOnce({ current: '2.1.1', state: { phase: 'handed_over', to: '2.2.0' } })
    .mockRejectedValueOnce(new Error('Server restarting'))
    .mockResolvedValue(completed);
  const view = await setup();
  await act(async () => { await vi.advanceTimersByTimeAsync(1600); });
  expect(reload).not.toHaveBeenCalled();
  expect(screen.getByRole('status')).toHaveTextContent('settings.updatePhaseRestarting');
  await act(async () => { await vi.advanceTimersByTimeAsync(15000); });
  expect(reload).toHaveBeenCalledTimes(1);
  expect(api.updateState).toHaveBeenCalledTimes(3);
  view.unmount();

  vi.mocked(api.updateStatus).mockResolvedValue({ ...release, current: '2.2.0', update_available: false });
  await setup();
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(reload).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'settings.updateCheckNow' })).toBeEnabled();
  expect(api.updateState).toHaveBeenCalledTimes(4);
});

/** A retained completion event describes the previous operation. It cannot
 * replace proof that the target of the update being observed is now serving. */
it('waits for the target version when a previous completion is still returned', async () => {
  vi.mocked(api.updateState)
    .mockResolvedValueOnce({ current: '2.1.1', state: { phase: 'pulling', to: '2.2.0' } })
    .mockResolvedValue({ current: '2.1.1', state: { phase: 'done', to: '2.1.1' } });
  await setup();
  await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
  expect(reload).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: 'settings.updateCheckNow' })).toBeDisabled();
  vi.mocked(api.updateState).mockResolvedValue({ current: '2.2.0', state: null });
  await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
  expect(reload).toHaveBeenCalledTimes(1);
});

it('keeps a failed update visible and permits a deliberate retry', async () => {
  vi.mocked(api.updateState).mockResolvedValueOnce({ current: '2.1.1', state: { phase: 'pulling', to: '2.2.0' } })
    .mockResolvedValue({ current: '2.1.1', state: { phase: 'failed', error: 'Registry unavailable' } });
  await setup();
  await act(async () => { await vi.advanceTimersByTimeAsync(1600); });
  expect(screen.getByRole('alert')).toHaveTextContent('Registry unavailable');
  expect(screen.getByRole('button', { name: 'settings.updateApplyNow' })).toBeEnabled();
});

it('requires confirmation and prevents repeated apply clicks during the request', async () => {
  vi.mocked(api.updateApply).mockImplementation(() => new Promise(() => {}));
  await setup();
  fireEvent.click(screen.getByRole('button', { name: 'settings.updateApplyNow' }));
  expect(api.updateApply).not.toHaveBeenCalled();
  const confirmation = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'settings.updateApplyNow' });
  fireEvent.click(confirmation);
  expect(api.updateApply).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button', { name: 'settings.updateApplyNow' })).toBeDisabled();
});

/** A slow apply response must not let the old operation stop the observer
 * before the new target has even been accepted by the server. */
it('starts observing only after the apply request accepts the target', async () => {
  let accept!: (answer: { started: boolean; to: string }) => void;
  vi.mocked(api.updateApply).mockImplementation(() => new Promise(resolve => { accept = resolve; }));
  vi.mocked(api.updateState).mockResolvedValue({ current: '2.1.1', state: { phase: 'done', to: '2.1.1' } });
  await setup();
  fireEvent.click(screen.getByRole('button', { name: 'settings.updateApplyNow' }));
  fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'settings.updateApplyNow' }));
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(api.updateState).toHaveBeenCalledTimes(1);
  expect(reload).not.toHaveBeenCalled();
  await act(async () => { accept({ started: true, to: '2.2.0' }); });
  vi.mocked(api.updateState).mockResolvedValue({ current: '2.2.0', state: { phase: 'stopping', to: '2.2.0' } });
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(reload).toHaveBeenCalledTimes(1);
  expect(api.updateState).toHaveBeenCalledTimes(2);
});
