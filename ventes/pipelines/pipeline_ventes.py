"""Four explicit steps, CPU only; compile with KFP SDK 2.16.0."""
from kfp import dsl, compiler
from kfp.dsl import Dataset, Model, Metrics, Input, Output

# Same supported CPU image as the workbench, pinned to the tested 3.5 digest.
# Its packages are already installed: no pip downloads during a live run.
BASE_IMAGE = 'registry.redhat.io/rhoai/odh-workbench-jupyter-datascience-cpu-py312-rhel9@sha256:b8d61ee1fa27f40677e32160cf34c34bea96a7ce981c32cea80efd387ab831e4'

@dsl.component(base_image=BASE_IMAGE, install_kfp_package=False)
def preparer(donnees: Output[Dataset]):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(42)
    dates = pd.date_range('2026-01-01', periods=210)
    temperature = np.round(19 + 8 * np.sin(np.arange(210) / 210 * np.pi) + rng.normal(0, 3, 210), 1)
    weekend = (dates.dayofweek >= 5).astype(int)
    promotion = rng.binomial(1, 0.25, 210)
    ventes = np.maximum(0, np.rint(40 + 4 * temperature + 35 * weekend + 45 * promotion + rng.normal(0, 8, 210))).astype(int)
    pd.DataFrame({'date': dates.strftime('%Y-%m-%d'), 'temperature_prevue': temperature,
                  'weekend': weekend, 'promotion': promotion, 'ventes': ventes}).to_csv(donnees.path, index=False)
    donnees.metadata['origine'] = 'Donnees synthetiques, graine 42'
    print('210 jours synthétiques préparés : 168 pour apprendre, 42 pour vérifier.')

@dsl.component(base_image=BASE_IMAGE, install_kfp_package=False)
def entrainer(donnees: Input[Dataset], modele: Output[Model]):
    import pickle
    import pandas as pd
    from sklearn.linear_model import LinearRegression
    df = pd.read_csv(donnees.path).sort_values('date').reset_index(drop=True)
    colonnes = ['temperature_prevue', 'weekend', 'promotion']
    train = df.iloc[:168]
    reg = LinearRegression().fit(train[colonnes], train.ventes)
    with open(modele.path, 'wb') as f:
        pickle.dump({'model': reg, 'baseline': float(train.ventes.mean()), 'features': colonnes}, f)
    modele.metadata['algorithme'] = 'LinearRegression'
    modele.metadata['jours_apprentissage'] = 168
    print('Régression linéaire entraînée sur les 168 premiers jours.')

@dsl.component(base_image=BASE_IMAGE, install_kfp_package=False)
def evaluer(donnees: Input[Dataset], modele: Input[Model], qualite: Output[Metrics]) -> float:
    import pickle
    import numpy as np
    import pandas as pd
    from sklearn.metrics import mean_absolute_error
    # Only load the artifact produced by our own training step.
    with open(modele.path, 'rb') as f: bundle = pickle.load(f)
    test = pd.read_csv(donnees.path).sort_values('date').reset_index(drop=True).iloc[168:]
    mae = float(mean_absolute_error(test.ventes, bundle['model'].predict(test[bundle['features']])))
    baseline = float(mean_absolute_error(test.ventes, np.full(len(test), bundle['baseline'])))
    qualite.log_metric('mae_modele', mae)
    qualite.log_metric('mae_reference', baseline)
    qualite.log_metric('jours_test', len(test))
    print(f'Erreur moyenne : modèle {mae:.1f} glaces/jour ; référence {baseline:.1f}.')
    return mae

@dsl.component(base_image=BASE_IMAGE, install_kfp_package=False)
def prevoir(modele: Input[Model], mae_test: float, temperature: float, weekend: int,
            promotion: int, prevision: Output[Dataset]) -> int:
    import pickle
    import pandas as pd
    if weekend not in (0, 1) or promotion not in (0, 1):
        raise ValueError('weekend et promotion doivent valoir 0 ou 1')
    with open(modele.path, 'rb') as f: bundle = pickle.load(f)
    demain = pd.DataFrame([{'temperature_prevue': temperature, 'weekend': weekend, 'promotion': promotion}])
    quantite = max(0, round(float(bundle['model'].predict(demain[bundle['features']])[0])))
    pd.DataFrame([{'date_scenario': '2026-08-01', 'temperature_prevue': temperature,
                  'weekend': weekend, 'promotion': promotion, 'ventes_prevues': quantite,
                  'mae_test': mae_test}]).to_csv(prevision.path, index=False)
    prevision.metadata['ventes_prevues'] = quantite
    print(f'PRÉVISION : {quantite} glaces. Erreur moyenne du test : {mae_test:.1f}.')
    print('Données synthétiques ; cette erreur moyenne n’est pas un intervalle de confiance.')
    return quantite

@dsl.pipeline(name='prevoir-les-ventes', description='Démo pédagogique CPU : préparer, entraîner, évaluer et prévoir les ventes de glaces.')
def pipeline_ventes(temperature: float = 24.0, weekend: int = 1, promotion: int = 1):
    data = preparer().set_display_name('1 Préparer les données')
    model = entrainer(donnees=data.outputs['donnees']).set_display_name('2 Entraîner le modèle')
    quality = evaluer(donnees=data.outputs['donnees'], modele=model.outputs['modele']).set_display_name('3 Évaluer la qualité')
    prediction = prevoir(modele=model.outputs['modele'], mae_test=quality.outputs['Output'],
                        temperature=temperature, weekend=weekend, promotion=promotion).set_display_name('4 Prévoir demain')
    for task in [data, model, quality, prediction]:
        task.set_caching_options(False)
        task.set_cpu_request('250m').set_cpu_limit('1')
        task.set_memory_request('512Mi').set_memory_limit('1Gi')

if __name__ == '__main__':
    from pathlib import Path
    compiler.Compiler().compile(pipeline_ventes, str(Path(__file__).resolve().parents[1] / 'pipeline_ventes.yaml'))
