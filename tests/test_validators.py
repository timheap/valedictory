from valedictory import InvalidDataException, Validator, fields
from valedictory.exceptions import ValidationException
from valedictory.validator import partition_dict

from .utils import ValidatorTestCase


class TestValidators(ValidatorTestCase):

    def test_cleaning_fields(self):
        validator = Validator(fields={
            'int': fields.IntegerField(),
            'string': fields.StringField()})

        data = {'int': 10, 'string': 'foo'}
        cleaned_data = validator.clean(data)

        self.assertEqual(data, cleaned_data)

    def test_unknown_fields_disallowed(self):
        """
        Unknown fields should throw an error
        """
        validator = Validator(fields={
            'int': fields.IntegerField(),
            'string': fields.StringField()})

        data = {'int': 10, 'string': 'foo', 'nope': 'nope'}
        with self.assertRaises(InvalidDataException) as cm:
            validator.clean(data)
        errors = cm.exception
        self.assertEqual(['nope'], sorted(errors.invalid_fields.keys()))
        self.assertEqual(errors, InvalidDataException({
            'nope': [ValidationException('Unknown field', 'unknown')]}))

    def test_unknown_fields_allowed(self):
        """
        Unknown fields can be silently allowed by setting a flag
        """
        validator = Validator(allow_unknown_fields=True, fields={
            'int': fields.IntegerField(),
            'string': fields.StringField()})

        cleaned_data = validator.clean({'int': 10, 'string': 'foo', 'nope': 'nope'})

        self.assertEqual({'int': 10, 'string': 'foo'}, cleaned_data)

    def test_not_required_fields(self):
        """
        Optional fields should be optional
        """
        validator = Validator(fields={
            'int': fields.IntegerField(required=False),
            'string': fields.StringField(required=False)})

        self.assertEqual({}, validator.clean({}))
        self.assertEqual({'int': 10}, validator.clean({'int': 10}))
        self.assertEqual({'string': 'foo'}, validator.clean({'string': 'foo'}))
        self.assertEqual({'int': 10, 'string': 'foo'},
                         validator.clean({'int': 10, 'string': 'foo'}))


class TestDeclarativeValidators(ValidatorTestCase):

    def test_no_inheritance(self):
        class MyValidator(Validator):
            int = fields.IntegerField()
            string = fields.StringField()

        self.assertEqual(
            sorted(MyValidator.fields.keys()),
            ['int', 'string'])

        data = {'int': 10, 'string': 'foo'}
        cleaned_data = MyValidator().clean(data)
        self.assertEqual(data, cleaned_data)

    def test_single_inheritance(self):
        class ParentValidator(Validator):
            int = fields.IntegerField()

        class ChildValidator(ParentValidator):
            string = fields.StringField()

        self.assertEqual(
            sorted(ChildValidator.fields.keys()),
            ['int', 'string'])

    def test_multiple_inheritance(self):
        class P1Validator(Validator):
            int = fields.IntegerField()
            override = fields.BooleanField()

        class P2Validator(Validator):
            string = fields.StringField()
            override = fields.DateField()

        class ChildValidator(P1Validator, P2Validator):
            email = fields.EmailField()

        self.assertEqual(
            sorted(ChildValidator.fields.keys()),
            sorted(['email', 'int', 'override', 'string']))

        # Field overriding should occur in MRO order, so override should have
        # come from P1Validator
        self.assertIsInstance(ChildValidator.fields['override'],
                              fields.BooleanField)

    def test_methods_and_attributes(self):
        class MyValidator(Validator):
            int = fields.IntegerField()
            string = fields.StringField()

            bar = "baz"

            def do_thing(self):
                return "foo"

        self.assertEqual(
            sorted(MyValidator.fields.keys()),
            ['int', 'string'])

        validator = MyValidator()
        data = {'int': 10, 'string': 'foo'}
        cleaned_data = validator.clean(data)

        self.assertEqual(data, cleaned_data)
        self.assertEqual("foo", validator.do_thing())
        self.assertEqual("baz", validator.bar)


class TestMisc(ValidatorTestCase):
    def test_partition_dict(self):
        keys = set()
        values = set()

        def pred(key, value):
            keys.add(key)
            values.add(value)
            return key % 2 == 0

        d = {i: chr(i + 65) for i in range(10)}
        odd, even = partition_dict(d, pred)

        self.assertEqual(odd, {1: 'B', 3: 'D', 5: 'F', 7: 'H', 9: 'J'})
        self.assertEqual(even, {0: 'A', 2: 'C', 4: 'E', 6: 'G', 8: 'I'})
        self.assertEqual(keys, set(range(10)))
        self.assertEqual(values, set("ABCDEFGHIJ"))


class ModuloIntValidator(fields.IntegerField):
    modulo = None

    def set_modulo(self, modulo):
        self.modulo = modulo


class ModuloValidator(Validator):
    single = ModuloIntValidator()
    double = ModuloIntValidator()

    def __init__(self, modulo: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['single'].set_modulo(modulo)
        self.fields['double'].set_modulo(modulo * 2)


class TestCopy(ValidatorTestCase):
    def test_basic(self):
        # Make sure things start as None
        self.assertIsNone(ModuloValidator.fields['single'].modulo)
        self.assertIsNone(ModuloValidator.fields['double'].modulo)

        # Make a modulo 3 validator
        modulo_3 = ModuloValidator(3)
        # Check it set modulo on its child validators
        self.assertEquals(modulo_3.fields['single'].modulo, 3)
        self.assertEquals(modulo_3.fields['double'].modulo, 6)
        # Check the base validator was not mutated
        self.assertIsNone(ModuloValidator.fields['single'].modulo)
        self.assertIsNone(ModuloValidator.fields['double'].modulo)

        # Make a modulo 7 validator
        modulo_7 = ModuloValidator(7)
        # Check it set modulo on its child validators
        self.assertEquals(modulo_7.fields['single'].modulo, 7)
        self.assertEquals(modulo_7.fields['double'].modulo, 14)
        # Check the other validator was not mutated
        self.assertEquals(modulo_3.fields['single'].modulo, 3)
        self.assertEquals(modulo_3.fields['double'].modulo, 6)
        # Check the base validator was not mutated
        self.assertIsNone(ModuloValidator.fields['single'].modulo)
        self.assertIsNone(ModuloValidator.fields['double'].modulo)
