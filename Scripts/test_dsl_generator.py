import os
import json
import unittest
import subprocess


class TestDSLGenerator(unittest.TestCase):
    def setUp(self):
        self.scripts_dir = os.path.dirname(__file__)
        self.config = os.path.join(self.scripts_dir, "config.ini")
        self.output_dir = os.path.join(self.scripts_dir, "monitors")
        # Clean output dir
        if os.path.exists(self.output_dir):
            for f in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, f))

    def test_generate_and_validate_json(self):
        # Run the generator
        # run the enhanced generator from utility/
        gen_path = os.path.join(self.scripts_dir, "utility", "dsl_generator.py")
        proc = subprocess.run(["python3", gen_path, "--config", self.config], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=f"Generator failed: {proc.stderr}")

        # Determine output dir from config (relative to project root)
        # Read config to get output_dir value
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(self.config)
        out = cfg.get('general', 'output_dir', fallback='monitors')
        # if out is relative path, resolve from project root (cwd at test run)
        out_path = os.path.abspath(out)
        self.assertTrue(os.path.isdir(out_path), f"Output directory missing: {out_path}")
        files = [f for f in os.listdir(out_path) if f.endswith('.json')]
        self.assertGreaterEqual(len(files), 1, "No monitor JSON files generated")

        # Validate JSON structure for each file
        for fn in files:
            path = os.path.join(out_path, fn)
            with open(path) as fh:
                payload = json.load(fh)
            # Basic assertions
            self.assertIn('name', payload)
            self.assertIn('inputs', payload)
            self.assertIn('triggers', payload)
            self.assertIsInstance(payload['inputs'], list)
            self.assertIsInstance(payload['triggers'], list)


if __name__ == '__main__':
    unittest.main()
