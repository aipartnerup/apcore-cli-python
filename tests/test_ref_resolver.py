"""Tests for $ref resolver (FE-02)."""

import pytest
from apcore_cli.ref_resolver import resolve_refs


class TestResolveRefs:
    """Task 5: $ref resolution."""

    def test_resolve_simple_ref(self):
        schema = {
            "properties": {
                "address": {"$ref": "#/$defs/Address"},
            },
            "$defs": {
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                    },
                },
            },
        }
        result = resolve_refs(schema, module_id="test")
        # Address should be inlined
        addr = result["properties"]["address"]
        assert "properties" in addr
        assert "street" in addr["properties"]

    def test_resolve_nested_ref(self):
        schema = {
            "properties": {
                "user": {"$ref": "#/$defs/User"},
            },
            "$defs": {
                "User": {
                    "properties": {
                        "address": {"$ref": "#/$defs/Address"},
                    },
                },
                "Address": {
                    "properties": {
                        "city": {"type": "string"},
                    },
                },
            },
        }
        result = resolve_refs(schema, module_id="test")
        user = result["properties"]["user"]
        addr = user["properties"]["address"]
        assert "city" in addr["properties"]

    def test_resolve_circular_ref(self):
        schema = {
            "properties": {
                "node": {"$ref": "#/$defs/A"},
            },
            "$defs": {
                "A": {"properties": {"next": {"$ref": "#/$defs/B"}}},
                "B": {"properties": {"next": {"$ref": "#/$defs/A"}}},
            },
        }
        with pytest.raises(SystemExit) as exc_info:
            resolve_refs(schema, module_id="test")
        assert exc_info.value.code == 48

    def test_resolve_depth_exceeded(self):
        # Build a chain of 33 refs
        defs = {}
        for i in range(33):
            next_key = f"R{i + 1}" if i < 32 else "R32"
            defs[f"R{i}"] = {"$ref": f"#/$defs/{next_key}"}
        defs["R32"] = {"type": "string"}
        schema = {
            "properties": {"field": {"$ref": "#/$defs/R0"}},
            "$defs": defs,
        }
        with pytest.raises(SystemExit) as exc_info:
            resolve_refs(schema, max_depth=32, module_id="test")
        assert exc_info.value.code == 48

    def test_resolve_unresolvable_ref(self):
        schema = {
            "properties": {
                "field": {"$ref": "#/$defs/Missing"},
            },
            "$defs": {},
        }
        with pytest.raises(SystemExit) as exc_info:
            resolve_refs(schema, module_id="test")
        assert exc_info.value.code == 45

    def test_resolve_no_refs(self):
        schema = {
            "properties": {
                "name": {"type": "string"},
            },
        }
        result = resolve_refs(schema, module_id="test")
        assert result["properties"]["name"]["type"] == "string"

    def test_resolve_removes_defs(self):
        schema = {
            "properties": {"name": {"type": "string"}},
            "$defs": {"Foo": {"type": "integer"}},
        }
        result = resolve_refs(schema, module_id="test")
        assert "$defs" not in result
        assert "definitions" not in result


class TestComposition:
    """Task 6: allOf, anyOf, oneOf flattening."""

    def test_allof_merge_properties(self):
        schema = {
            "allOf": [
                {"properties": {"a": {"type": "string"}}, "required": ["a"]},
                {"properties": {"b": {"type": "integer"}}, "required": ["b"]},
            ],
        }
        result = resolve_refs(schema, module_id="test")
        assert "a" in result["properties"]
        assert "b" in result["properties"]
        assert "a" in result["required"]
        assert "b" in result["required"]

    def test_allof_later_overrides(self):
        schema = {
            "allOf": [
                {"properties": {"x": {"type": "string"}}},
                {"properties": {"x": {"type": "integer"}}},
            ],
        }
        result = resolve_refs(schema, module_id="test")
        assert result["properties"]["x"]["type"] == "integer"

    def test_anyof_union_properties(self):
        schema = {
            "anyOf": [
                {"properties": {"a": {"type": "string"}}},
                {"properties": {"b": {"type": "integer"}}},
            ],
        }
        result = resolve_refs(schema, module_id="test")
        assert "a" in result["properties"]
        assert "b" in result["properties"]

    def test_anyof_required_intersection(self):
        schema = {
            "anyOf": [
                {"properties": {"a": {"type": "string"}, "b": {"type": "string"}}, "required": ["a", "b"]},
                {"properties": {"a": {"type": "string"}, "c": {"type": "string"}}, "required": ["a", "c"]},
            ],
        }
        result = resolve_refs(schema, module_id="test")
        # Only "a" is required in BOTH branches
        assert "a" in result["required"]
        assert "b" not in result["required"]
        assert "c" not in result["required"]

    def test_oneof_same_as_anyof(self):
        schema = {
            "oneOf": [
                {"properties": {"x": {"type": "string"}}},
                {"properties": {"y": {"type": "integer"}}},
            ],
        }
        result = resolve_refs(schema, module_id="test")
        assert "x" in result["properties"]
        assert "y" in result["properties"]

    def test_nested_composition(self):
        schema = {
            "allOf": [
                {"$ref": "#/$defs/Base"},
                {"properties": {"extra": {"type": "string"}}},
            ],
            "$defs": {
                "Base": {
                    "properties": {"id": {"type": "integer"}},
                    "required": ["id"],
                },
            },
        }
        result = resolve_refs(schema, module_id="test")
        assert "id" in result["properties"]
        assert "extra" in result["properties"]
        assert "id" in result["required"]
