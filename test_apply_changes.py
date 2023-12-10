import unittest
from wikibrain.apply_changes import apply_changes
from wikibrain.apply_changes import PrerequisiteFailedError


class Tests(unittest.TestCase):
    def test_for_apply_changes_function_presence(self):
        tags = {}
        change = {}
        apply_changes(tags, change)

    def test_simplest_applying_changes(self):
        tags = {'wikipedia': 'en:Walmart Market'}
        change = [{'to': {'wikipedia': 'en:Walmart'}, 'from': {'wikipedia': 'en:Walmart Market'}}]
        tags = apply_changes(tags, change)
        self.assertEqual({"wikipedia": "en:Walmart"}, tags)

    def test_exception_on_changing_nonexisting(self):
        self.assertRaises(PrerequisiteFailedError, apply_changes, {}, [{'from': {'key': 'value'}, 'to': {}}])

    def test_from_values_are_deleted(self):
        change = [{'from': {'key': 'value'}, 'to': {}}]
        tags = apply_changes({'key': 'value'}, change)
        self.assertEqual({}, tags)

    def test_from_values_are_deleted_on_specifying_none(self):
        change = [{'from': {'key': 'value'}, 'to': {'key': None}}]
        tags = apply_changes({'key': 'value'}, change)
        self.assertEqual({}, tags)

    def test_keys_may_be_changed(self):
        change = [{'from': {'key': 'value'}, 'to': {'new_key': 'qweert'}}]
        tags = apply_changes({'key': 'value'}, change)
        self.assertEqual({'new_key': 'qweert'}, tags)

    def test_demand_explicit_key_change(self):
        self.assertRaises(PrerequisiteFailedError, apply_changes, {'key': 'value'}, [{'from': {}, 'to': {'key': 'value'}}])

    def test_keys_may_be_added(self):
        change = [{'from': {}, 'to': {'new_key': 'qweert'}}]
        tags = apply_changes({'key': 'value'}, change)
        self.assertEqual({'key': 'value', 'new_key': 'qweert'}, tags)

    def test_keys_may_be_added_to_empty_object(self):
        change = [{'from': {}, 'to': {'new_key': 'qweert'}}]
        tags = apply_changes({}, change)
        self.assertEqual({'new_key': 'qweert'}, tags)

    def test_keys_may_be_added_previous_state_specified_by_none(self):
        change = [{'from': {'new_key': None}, 'to': {'new_key': 'qweert'}}]
        tags = apply_changes({'key': 'value'}, change)
        self.assertEqual({'key': 'value', 'new_key': 'qweert'}, tags)


if __name__ == '__main__':
    unittest.main()
