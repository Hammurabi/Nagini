import unittest

from nagini.compiler import NaginiParser, NaginiIR, LLVMBackend


class BackendSubscriptTests(unittest.TestCase):
    def _generate_code(self, source: str) -> str:
        parser = NaginiParser()
        classes, functions, top_level = parser.parse(source)
        ir = NaginiIR(classes, functions, top_level).generate()
        backend = LLVMBackend(ir)
        return backend.generate()

    def test_subscript_access_uses_runtime_helper(self):
        code = self._generate_code(
            "def main():\n"
            "    t = (1, 2)\n"
            "    x = t[0]\n"
        )
        self.assertIn("NgGetItem(runtime, t, runtime->constants[", code)

    def test_subscript_assignment_uses_runtime_helper(self):
        code = self._generate_code(
            "def main():\n"
            "    arr = (1, 2)\n"
            "    arr[0] = 5\n"
        )
        self.assertIn("NgSetItem(runtime, arr, runtime->constants[", code)


if __name__ == "__main__":
    unittest.main()
