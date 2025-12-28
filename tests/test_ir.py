import unittest

from nagini.compiler import NaginiParser, NaginiIR
from nagini.compiler.ir import (
    AssignIR,
    ConstantIR,
    MultiAssignIR,
    SliceIR,
    SubscriptIR,
    SubscriptAssignIR,
    VariableIR,
)


class IRGenerationTests(unittest.TestCase):
    def _main_body(self, source: str):
        parser = NaginiParser()
        classes, functions, top_level = parser.parse(source)
        ir = NaginiIR(classes, functions, top_level).generate()
        main_func = next(f for f in ir.functions if f.name == "main")
        return main_func.body

    def test_tuple_unpack_creates_multi_assign(self):
        body = self._main_body("a, b = (1, 2)")
        self.assertIsInstance(body[0], MultiAssignIR)
        assigns = body[0].assignments
        self.assertEqual(len(assigns), 4)
        self.assertTrue(all(a.target.startswith("__tmp_unpack_") for a in assigns[:2]))
        self.assertIsInstance(assigns[2], AssignIR)
        self.assertEqual(assigns[2].target, "a")
        self.assertEqual(assigns[3].target, "b")

    def test_subscript_slicing_ir(self):
        body = self._main_body("x = arr[1:5:2]")
        self.assertIsInstance(body[0], AssignIR)
        value = body[0].value
        self.assertIsInstance(value, SubscriptIR)
        self.assertIsInstance(value.index, SliceIR)
        self.assertIsNotNone(value.index.start)
        self.assertIsNotNone(value.index.stop)
        self.assertIsNotNone(value.index.step)

    def test_subscript_assignment_ir(self):
        body = self._main_body("arr[0] = 3")
        self.assertIsInstance(body[0], SubscriptAssignIR)
        self.assertIsInstance(body[0].index, ConstantIR)

    def test_tuple_unpack_uses_temporaries_for_swap(self):
        body = self._main_body("x = 1\ny = 2\nx, y = y, x")
        self.assertIsInstance(body[2], MultiAssignIR)
        assigns = body[2].assignments
        self.assertTrue(all(a.target.startswith("__tmp_unpack_") for a in assigns[:2]))
        self.assertIsInstance(assigns[2].value, VariableIR)
        self.assertIsInstance(assigns[3].value, VariableIR)
        self.assertTrue(assigns[2].value.name.startswith("__tmp_unpack_"))
        self.assertTrue(assigns[3].value.name.startswith("__tmp_unpack_"))


if __name__ == "__main__":
    unittest.main()
