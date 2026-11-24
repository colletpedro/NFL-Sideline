"""New pin and copied original sources. Existing packages are read-only inputs."""
import json
from pathlib import Path
import shutil
import tempfile

import polars as pl

from ..comparison_foundation.package import hashes
from ..matchup_w12.package import read as read_matchups
from ..metrics_observations.publication import exact_tree
from ..offline_metrics.artifact import rename_exclusive
from ..situational import safe, digest, encoded
from . import VERSION, SOURCE_PIN
from .project import project

DEFINITION = '''# EPA por jogada que começa na red zone · 1.0.0

População classified-scrimmage-v1, restringida à posição observada antes da jogada: 0 < yardline_100 <= 20.
Passe/run classificados, sacks e scrambles incluídos; exclusões e flags herdadas. Não inclui chutes, punts, ajoelhadas,
spikes, anuladas ou tentativas especiais. Uma jogada que começa fora não entra por terminar dentro; uma que começa
dentro entra mesmo se termina fora. Não soma toda a campanha que visitou a red zone.

EPA/jogada = soma exata dos EPA finitos / jogadas elegíveis com EPA finito. Soma usa Fraction(str(Float64)),
sem arredondamento intermediário. EPA ausente/não finito é contado separadamente e não vira zero. Flags/posição
indeterminadas em candidatos impedem apresentar a média. Sem oportunidades é diferente de fonte ausente.
Agregado soma os valores e reúne IDs únicos dos dois jogos; componente ausente impede média do agregado.

TD/campanha e EPA/jogada têm unidades e denominadores distintos. A definição de campanha permanece intacta.
Comparações somente descritivas, com mesma regra, fonte e período e ambos AVAILABLE. Não há ranking EPA,
qualidade geral, significância, previsão, certificação do modelo ou independência ataque/defesa adversária.
Completude, cobertura esperada, modelo EPA e conhecimento temporal continuam UNKNOWN.
'''


def derive(root):
    index, docs, _ = read_matchups(root/'source', SOURCE_PIN)
    raw = root/'source/sources/situational/pbp.parquet'
    rows = pl.read_parquet(raw).sort('game_id', 'order_sequence').to_dicts()
    if digest(raw.read_bytes()) != index['sources']['pbpHash']:
        raise ValueError('Red zone raw source hash mismatch')
    return encoded(project(index, {k: json.loads(v) for k, v in docs.items()}, rows, index['sources']['pbpHash']))


def read(root, expected_pin=None):
    root = safe(root)
    marker = json.loads((root/'COMPLETED.json').read_bytes())
    if set(marker) != {'version', 'bundleId', 'files'} or marker['version'] != VERSION:
        raise ValueError('Invalid red zone package marker')
    names = {'redzone-epa.json', 'definition.md'} | {'source/'+n for n in hashes(root/'source')}
    exact_tree(root, names | {'COMPLETED.json'})
    payload = (root/'redzone-epa.json').read_bytes()
    pin = digest(payload)
    if marker['bundleId'] != pin or expected_pin is not None and expected_pin != pin:
        raise ValueError('Red zone EPA pin mismatch')
    if marker['files'] != {n: digest((root/n).read_bytes()) for n in names}:
        raise ValueError('Red zone EPA package hash mismatch')
    if (root/'definition.md').read_text() != DEFINITION or derive(root) != payload:
        raise ValueError('Red zone EPA semantic derivation mismatch')
    return payload, marker


def generate(source, output):
    source, output = safe(source), safe(output)
    if output.exists() or source == output or source in output.parents or output in source.parents:
        raise ValueError('New disjoint destination required')
    read_matchups(source, SOURCE_PIN)
    before = hashes(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.'+output.name+'.pending-', dir=output.parent))
    try:
        shutil.copytree(source, stage/'source')
        if hashes(source) != before or hashes(stage/'source') != before:
            raise ValueError('Original source changed during copy')
        (stage/'definition.md').write_text(DEFINITION)
        payload = derive(stage)
        (stage/'redzone-epa.json').write_bytes(payload)
        marker = dict(version=VERSION, bundleId=digest(payload), files=hashes(stage))
        (stage/'COMPLETED.json').write_bytes(encoded(marker))
        read(stage, marker['bundleId'])
        rename_exclusive(stage, output)
        return marker
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def reproduce(source, output):
    source = safe(source)
    _, original = read(source)
    marker = generate(source/'source', output)
    if marker != original or hashes(source) != hashes(safe(output)):
        raise ValueError('Red zone EPA reproduction mismatch')
    return marker
