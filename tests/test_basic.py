import unittest


class AppBehaviorTest(unittest.TestCase):
    def test_imports(self):
        import importlib

        module = importlib.import_module('app')
        self.assertTrue(hasattr(module, 'create_app'))

    def test_login_route_exists(self):
        import importlib

        module = importlib.import_module('app')
        app = module.create_app()
        self.assertIn('main.login', {rule.endpoint for rule in app.url_map.iter_rules()})


if __name__ == '__main__':
    unittest.main()
