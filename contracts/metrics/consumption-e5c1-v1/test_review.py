"""Contraprovas de revisão: testemunhas finitas, sem seletor PIT ou consumidor."""
import copy
import unittest

import verify


class ReviewWitnesses(unittest.TestCase):
    def setUp(self):
        self.fixtures = verify.load("examples.json")

    def changed(self, case_id, mutation):
        documents = copy.deepcopy(self.fixtures["observations"])
        case = copy.deepcopy(next(c for c in self.fixtures["cases"] if c["id"] == case_id))
        d = documents[case["observations"][1]]
        mutation(d)
        d["observationId"] = verify.semantic_identity(d)
        verify.validate_document(d)
        return case, documents

    def check_refusal(self, case, documents, witness, comparison):
        before = copy.deepcopy(documents)
        # A contraprova exige que as permissões antigas não passem sem mudança.
        with self.assertRaisesRegex(ValueError, "WITNESS_MISMATCH"):
            verify.check_case(case, documents)
        case["witnesses"].remove(witness)
        for family, results in case["expected"].items():
            if comparison:
                for op in verify.NUMERIC_OPS:
                    results[op].update(decision="REFUSE", scope=None,
                                       reasonCodes=["MISSING_REQUIRED_GUARANTEE"])
                    results[op]["missingRequirements"] = sorted(
                        set(results[op]["missingRequirements"]) | {witness})
                if family in {"epa", "successRate"}:
                    results["highlight"].update(decision="REFUSE",
                                                reasonCodes=["MISSING_REQUIRED_GUARANTEE"])
            results["pregameData"].update(decision="REFUSE",
                                           reasonCodes=["PREGAME_REQUIREMENTS_NOT_MET"])
            results["pregameData"]["missingRequirements"] = sorted(
                set(results["pregameData"]["missingRequirements"]) | {witness})
        verify.check_case(case, documents)
        self.assertEqual(documents, before)
        self.assertTrue(all(documents[r]["values"]["epa"] is not None
                            for r in case["observations"]))

    def test_basic_conflict_and_unknown_refuse_comparison(self):
        for state in ("CONFLICT", "UNKNOWN"):
            with self.subTest(state=state):
                case, docs = self.changed("descriptive_not_pregame", lambda d:
                    d["guarantees"]["compatibility"].update(
                        state=state, reasonCodes=["INCOMPATIBLE_DEFINITION_OR_POPULATION"]))
                self.check_refusal(case, docs, "BASIC_MATCH", comparison=True)

    def test_distinct_cutoffs_refuse_comparison_and_pregame(self):
        case, docs = self.changed("pregame_data_only", lambda d:
            d["guarantees"]["temporal"].update(cutoff="2025-09-10T13:00:00Z"))
        self.check_refusal(case, docs, "BASIC_MATCH", comparison=True)

    def test_target_in_members_refuses_pregame_preserving_description(self):
        # Keep the same target/kickoff across both sides to isolate exclusion.
        case, docs = self.changed("pregame_data_only", lambda d: None)
        target = docs[case["observations"][0]]["members"][0]["gameId"]
        for ref in case["observations"]:
            docs[ref]["guarantees"]["temporal"]["targetGameId"] = target
            docs[ref]["observationId"] = verify.semantic_identity(docs[ref])
            verify.validate_document(docs[ref])
        self.check_refusal(case, docs, "PREGAME_CUTOFF", comparison=False)

    def test_distinct_or_missing_targets_refuse_pregame(self):
        for target in ("synthetic-other-target", None):
            with self.subTest(target=target):
                case, docs = self.changed("pregame_data_only", lambda d:
                    d["guarantees"]["temporal"].update(targetGameId=target))
                self.check_refusal(case, docs, "PREGAME_CUTOFF", comparison=False)

    def test_missing_cutoff_refuses_without_type_error(self):
        case, docs = self.changed("pregame_data_only", lambda d:
            d["guarantees"]["temporal"].update(cutoff=None))
        with self.assertRaisesRegex(ValueError, "WITNESS_MISMATCH"):
            verify.check_case(case, docs)


if __name__ == "__main__":
    unittest.main()
