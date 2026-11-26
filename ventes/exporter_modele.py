"""Run inside the workbench: train the same demo model and publish ONNX to S3."""
from pathlib import Path
import json
import os

import boto3
import numpy as np
import pandas as pd
import onnx
from onnx import TensorProto, helper, numpy_helper
from onnx.reference import ReferenceEvaluator
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

def publier(modele, donnees):
    """Publish the trained notebook model, checking float32 export accuracy."""
    colonnes = ['temperature_prevue', 'weekend', 'promotion']
    test = donnees.sort_values('date').reset_index(drop=True).iloc[168:]
    # Standard ONNX operators express the coefficients learned by this exact model.
    # No handwritten sales formula and no second model with different weights.
    graphe = helper.make_graph(
        [helper.make_node('MatMul', ['donnees', 'coefficients'], ['produit']),
         helper.make_node('Add', ['produit', 'constante'], ['ventes'])],
        'Prevision des ventes',
        [helper.make_tensor_value_info('donnees', TensorProto.FLOAT, [None, 3])],
        [helper.make_tensor_value_info('ventes', TensorProto.FLOAT, [None, 1])],
        [numpy_helper.from_array(modele.coef_.astype(np.float32).reshape(3, 1), 'coefficients'),
         numpy_helper.from_array(np.array([modele.intercept_], dtype=np.float32), 'constante')],
    )
    export = helper.make_model(graphe, opset_imports=[helper.make_opsetid('', 17)], ir_version=8)
    export.doc_string = 'Synthetic ice-cream sales; inputs: forecast temperature, weekend 0/1, promotion 0/1.'
    onnx.checker.check_model(export)
    reference = ReferenceEvaluator(export)
    attendu = modele.predict(test[colonnes])
    obtenu = reference.run(None, {'donnees': test[colonnes].to_numpy(dtype=np.float32)})[0].ravel()
    np.testing.assert_allclose(obtenu, attendu, rtol=1e-5, atol=1e-4)
    rapport = {'mae_modele': float(mean_absolute_error(test.ventes, attendu)),
               'ecart_max_export_onnx': float(np.max(np.abs(obtenu-attendu))),
               'jours_apprentissage': 168, 'jours_test': 42, 'colonnes': colonnes}
    Path('resultats').mkdir(exist_ok=True)
    Path('resultats/modele.onnx').write_bytes(export.SerializeToString())
    Path('resultats/export-modele.json').write_text(json.dumps(rapport, indent=2))

    s3 = boto3.client('s3', endpoint_url=os.environ['AWS_S3_ENDPOINT'],
                      region_name=os.environ['AWS_DEFAULT_REGION'])
    bucket = os.environ['AWS_S3_BUCKET']
    donnees.to_csv('resultats/ventes.csv', index=False)
    s3.upload_file('resultats/ventes.csv', bucket, 'donnees/ventes.csv')
    s3.upload_file('resultats/modele.onnx', bucket, 'modeles/ventes/1/model.onnx')
    s3.upload_file('resultats/export-modele.json', bucket, 'modeles/ventes/description.json')
    print('Données du magasin : connexion S3 opérationnelle.')
    print('Historique partagé : donnees/ventes.csv')
    print('Modèle prêt à déployer : modeles/ventes (format ONNX, version 1).')
    print(f'Export vérifié sur 42 jours. Écart maximal : {rapport["ecart_max_export_onnx"]:.6f} glace.')
    print('Le déploiement est une étape distincte dans OpenShift AI.')
    return rapport


if __name__ == '__main__':
    donnees = pd.read_csv('ventes.csv').sort_values('date').reset_index(drop=True)
    colonnes = ['temperature_prevue', 'weekend', 'promotion']
    apprentissage = donnees.iloc[:168]
    modele = LinearRegression().fit(apprentissage[colonnes], apprentissage.ventes)
    publier(modele, donnees)
