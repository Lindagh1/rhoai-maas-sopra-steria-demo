import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import demo
from client import request


class MaaSContractTests(unittest.TestCase):
    def setUp(self):
        self.config = demo.load_config(demo.ROOT/'config/demo.json')

    def test_render_is_stable_and_uses_real_native_backend(self):
        docs = demo.manifests(self.config)
        self.assertEqual(docs, demo.manifests(self.config))
        llm = next(x for x in docs if x['kind'] == 'LLMInferenceService')
        self.assertIn('hf://Qwen/', llm['spec']['model']['uri'])
        self.assertEqual(llm['spec']['template']['containers'][0]['resources']['limits']['nvidia.com/gpu'], '1')
        self.assertNotIn('simulator', json.dumps(llm))

    def test_cross_namespace_model_pairing_and_no_admin_grant(self):
        docs = demo.manifests(self.config)
        for d in docs:
            self.assertNotIn(d['kind'], ('ClusterRoleBinding', 'ClusterRole', 'Secret'))
            if d['kind'] == 'RoleBinding': self.assertEqual(d['roleRef']['name'], 'view')
            if d['kind'] in ('MaaSAuthPolicy', 'MaaSSubscription'):
                self.assertEqual(d['metadata']['namespace'], self.config['tenant_namespace'])
                self.assertEqual(d['spec']['modelRefs'][0]['namespace'], self.config['model_namespace'])
        by_name = {x['metadata']['name']: x for x in docs}
        self.assertEqual(by_name['sopra-access']['spec']['subjects'], by_name['sopra-standard']['spec']['owner'])

    def test_namespace_parameters_propagate(self):
        c = dict(self.config, model_namespace='test-models', gateway_name='test-gateway', gateway_namespace='test-infra')
        docs = demo.manifests(c)
        llm = next(d for d in docs if d['kind'] == 'LLMInferenceService')
        self.assertEqual(llm['spec']['router']['gateway']['refs'], [{'name': 'test-gateway', 'namespace': 'test-infra'}])
        self.assertNotIn('system:serviceaccount:sopra-maas-models:', json.dumps(docs))

    def test_collision_is_detected_before_any_mutation(self):
        obj = demo.manifests(self.config)[0]
        with patch.object(demo, 'check'), patch.object(demo, 'get', return_value={'metadata': {'labels': {}}}), patch.object(demo, 'oc') as call:
            with self.assertRaisesRegex(RuntimeError, 'Collision'):
                demo.apply(self.config)
            call.assert_not_called()

    def test_schema_failure_stops_apply_without_force(self):
        calls = []
        def run(*args, **kw):
            calls.append(args)
            if '--dry-run=server' in args: raise RuntimeError('schema incompatible')
        with patch.object(demo, 'check'), patch.object(demo, 'get', return_value=None), patch.object(demo, 'oc', side_effect=run):
            with self.assertRaisesRegex(RuntimeError, 'schema incompatible'):
                demo.apply(self.config)
        self.assertEqual(len(calls), 1)
        self.assertIn('--dry-run=server', calls[0])
        self.assertNotIn('--force-conflicts', calls[0])

    def test_negative_cases_do_not_withdraw_positive_access(self):
        docs = demo.manifests(self.config)
        policy = next(d for d in docs if d['metadata']['name'] == 'sopra-auth-only')
        sub = next(d for d in docs if d['metadata']['name'] == 'sopra-quota-only')
        self.assertIn(':auth-only', policy['spec']['subjects']['users'][0])
        self.assertIn(':quota-only', sub['spec']['owner']['users'][0])
        self.assertNotEqual(policy['spec']['subjects']['users'], sub['spec']['owner']['users'])

    def test_client_rejects_plain_http_and_header_injection(self):
        with self.assertRaises(ValueError): request('http://example.com', 'key', '/v1/models')
        with self.assertRaises(ValueError): request('https://example.com', 'key\nInjected: yes', '/v1/models')


if __name__ == '__main__': unittest.main()
