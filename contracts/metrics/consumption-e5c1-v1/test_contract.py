"""Acceptance properties over finite synthetic examples; not a future consumer."""
import copy
import hashlib
import json
from datetime import datetime
from fractions import Fraction
from decimal import Decimal
import unittest

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
import verify


class ContractProperties(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = verify.load("examples.json")
        cls.docs = cls.fixtures["observations"]

    def test_schema_and_all_valid_documents(self):
        Draft202012Validator.check_schema(verify.load("observation.schema.json"))
        for key, doc in self.docs.items():
            with self.subTest(key=key):
                verify.validate_document(doc)

    def test_all_operation_vectors(self):
        for case in self.fixtures["cases"]:
            with self.subTest(case=case["id"]):
                verify.check_case(case, self.docs)

    def test_invalid_cases_have_specific_failure_class(self):
        for case in self.fixtures["invalid"]:
            with self.subTest(case=case["id"]):
                error = ValidationError if case["failure"] == "SCHEMA" else ValueError
                with self.assertRaises(error):
                    verify.validate_document(verify.patched_invalid(case, self.docs))

    def test_reordering_and_replication_do_not_add_sample(self):
        # Test only canonical representation of already chosen members. No
        # aggregation or revision choice. Replica conflict is never last-wins.
        doc = self.docs["partial_sample-a"]
        member = doc["members"][0]
        other = copy.deepcopy(member)
        other["gameId"] = "synthetic-another-game"
        original = [member, other]
        for entries in (original, list(reversed(original)), original * 3):
            by_id = {}
            for m in entries:
                if m["gameId"] in by_id:
                    self.assertEqual(by_id[m["gameId"]], m)
                by_id[m["gameId"]] = m
            canonical = sorted(by_id.values(), key=lambda m: m["gameId"])
            self.assertEqual(canonical, sorted(original, key=lambda m: m["gameId"]))
            self.assertEqual(sum(m["statistics"]["eligibleN"] for m in canonical), 4)
            encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
            baseline = json.dumps(sorted(original, key=lambda m: m["gameId"]), sort_keys=True, separators=(",", ":")).encode()
            self.assertEqual(hashlib.sha256(encoded).digest(), hashlib.sha256(baseline).digest())

    def test_duplicate_game_alternative_is_invalid_document(self):
        doc = copy.deepcopy(self.docs["partial_sample-a"])
        alternate = copy.deepcopy(doc["members"][0])
        alternate["coverageRevisionId"] = "sha256:" + "f" * 64
        doc["members"].append(alternate)
        doc["members"].sort(key=lambda m: m["gameId"])
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_GAME_SELECTION"):
            verify.validate_document(doc, check_identity=False)

    def test_late_correction_does_not_change_frozen_choice(self):
        h = self.fixtures["history"][0]
        cutoff = datetime.fromisoformat(h["cutoff"])
        for key in ("availableAt", "ingestedAt", "evidenceReceivedAt"):
            self.assertLess(datetime.fromisoformat(h["before"][key]), cutoff)
            self.assertGreaterEqual(datetime.fromisoformat(h["correction"][key]), cutoff)
        self.assertEqual(h["expected"]["chosen"], h["before"]["revisionId"])
        self.assertEqual(h["expected"]["rejected"], h["correction"]["revisionId"])
        doc = self.docs[h["expected"]["unchangedObservationRef"]]
        frozen = verify.semantic_identity(doc)
        # Inelegible alternatives belong only to the external audit, no
        # alteration of members/guarantees of the frozen projection.
        audit = {"chosen": doc, "rejected": [h["correction"]]}
        self.assertEqual(verify.semantic_identity(audit["chosen"]), frozen)
        self.assertNotEqual(h["before"]["epaSum"], h["correction"]["epaSum"])

    def test_absence_empty_zero_and_no_denominator_are_distinct(self):
        absent = self.docs["absent_source-a"]
        empty = self.docs["empty_unknown-a"]
        complete = self.docs["empty_complete-a"]
        zero = self.docs["valid_zero-a"]
        no_epa = self.docs["no_epa-a"]
        self.assertIsNone(absent["totals"])
        self.assertEqual(empty["values"]["volume"], {"numerator":"0","denominator":1})
        self.assertEqual(empty["guarantees"]["completeness"]["state"], "UNKNOWN")
        self.assertEqual(complete["guarantees"]["completeness"]["state"], "COMPLETE")
        self.assertIsNone(complete["values"]["epa"])
        self.assertEqual(zero["values"]["epa"], {"numerator":"0","denominator":2})
        self.assertIsNone(no_epa["values"]["epa"])
        self.assertEqual(no_epa["values"]["volume"]["numerator"], "2")

    def test_refusing_comparison_preserves_individuals(self):
        before = copy.deepcopy(self.docs)
        for c in self.fixtures["cases"]:
            verify.check_case(c, self.docs)
        self.assertEqual(self.docs, before)
        case = next(c for c in self.fixtures["cases"] if c["id"] == "incompatible_period")
        self.assertEqual(case["expected"]["epa"]["align"]["decision"], "REFUSE")
        for ref in case["observations"]:
            self.assertIsNotNone(self.docs[ref]["values"]["epa"])
            self.assertTrue(self.docs[ref]["members"][0]["sourceRevisionIds"])

    def test_rounding_never_changes_semantic_identity(self):
        doc = copy.deepcopy(self.docs["reconciled_unknown-a"])
        identity = verify.semantic_identity(doc)
        doc["presentation"]["epaDecimals"] = 7
        doc["presentation"]["ratePercentDecimals"] = 4
        doc["derivedAt"] = "2026-10-14T12:00:00Z"
        self.assertEqual(verify.semantic_identity(doc), identity)
        verify.validate_document(doc)
        exact = doc["values"]["epa"]
        self.assertEqual(Fraction(Decimal(exact["numerator"])) / exact["denominator"], Fraction(1,2))

    def test_labels_cannot_strengthen_the_same_evidence(self):
        case = copy.deepcopy(next(c for c in self.fixtures["cases"] if c["id"] == "unknown_model"))
        case["witnesses"].append("MODEL_MATCH")
        with self.assertRaisesRegex(ValueError, "WITNESS_MISMATCH"):
            verify.check_case(case, self.docs)
        promoted = copy.deepcopy(self.docs["reconciled_unknown-a"])
        promoted["guarantees"]["completeness"]["state"] = "COMPLETE"
        with self.assertRaisesRegex(ValueError, "COMPLETENESS_NOT_PROMOTED"):
            verify.validate_document(promoted, check_identity=False)

    def test_conflicts_and_current_receipt_do_not_prove_history(self):
        conflict = self.fixtures["history"][1]
        self.assertEqual(len({d["value"] for d in conflict["declarations"]}), 2)
        self.assertTrue(all(not d["supersedes"] for d in conflict["declarations"]))
        self.assertEqual(conflict["expected"]["state"], "CONFLICT")
        self.assertTrue(conflict["expected"]["preserveBoth"])
        receipt = self.fixtures["history"][2]
        self.assertLess(receipt["eventAt"], receipt["cutoff"])
        self.assertGreater(receipt["receivedAt"], receipt["cutoff"])
        self.assertGreaterEqual(receipt["persistedAt"], receipt["receivedAt"])
        self.assertEqual(receipt["expected"]["historicalAvailability"], "UNKNOWN")
        self.assertEqual(receipt["expected"]["pregame"], "REFUSE")

    def test_real_illustration_does_not_create_provenance(self):
        real = self.fixtures["realIllustration"]
        self.assertEqual(real["kind"], "SUMMARY_ONLY_NOT_PROVENANCE")
        self.assertEqual(real["observedGames"], {"2025_REG":272,"2025_POST":13,"2026_REG_W1_2":32})
        self.assertEqual(real["pitAggregates"], "EMPTY")
        self.assertEqual(len(real["unknown"]), 5)
        self.assertNotIn("observationId", real)


if __name__ == "__main__":
    unittest.main()
