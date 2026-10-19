// Operator-only process boundary. No shell, dotenv, browser arguments or file cache.
import { execFile } from 'node:child_process';
import { isAbsolute, resolve } from 'node:path';
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const repo = resolve(fileURLToPath(new URL('../../', import.meta.url)));
export async function prepareSnapshot() {
  const config = process.env.NFL_OBSERVATION_CONFIG;
  const python = process.env.NFL_OBSERVATION_PYTHON;
  if (!config && !python) return { errorCode: 'OBSERVATIONS_NOT_CONFIGURED' };
  if (!config || !python || !isAbsolute(config) || !isAbsolute(python)) return { errorCode: 'OBSERVATION_CONFIGURATION_INVALID' };
  try { if (realpathSync(config).startsWith(`${repo}/web-ui/`)) return { errorCode: 'OBSERVATION_CONFIGURATION_INVALID' }; } catch { return { errorCode: 'OBSERVATION_CONFIGURATION_INVALID' }; }
  console.info('Observações: validando bundles configurados; aguardando a sessão congelada.');
  return new Promise(resolve => {
    const stop = () => child.kill('SIGTERM');
    const interrupt = () => { stop(); process.exit(130); };
    const terminate = () => { stop(); process.exit(143); };
    const child = execFile(python, ['-B', '-m', 'nfl_sideline_etl.metrics_lab', '--config', config], {
      cwd: repo, shell: false, encoding: 'utf8', timeout: 120000, maxBuffer: 8 * 1024 * 1024,
      env: { PATH: process.env.PATH, LANG: 'C.UTF-8', PYTHONPATH: `${repo}/etl-pipeline/src`, PYTHONDONTWRITEBYTECODE: '1' },
    }, (error, output) => {
      process.removeListener('exit', stop); process.removeListener('SIGINT', interrupt); process.removeListener('SIGTERM', terminate);
      if (error) resolve({ errorCode: 'OBSERVATION_STARTUP_FAILED' });
      else { try { resolve(JSON.parse(output)); } catch { resolve({ errorCode: 'OBSERVATION_STARTUP_FAILED' }); } }
    });
    process.once('exit', stop); process.once('SIGINT', interrupt); process.once('SIGTERM', terminate);
  });
}
