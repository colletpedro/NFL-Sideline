package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.nflsideline.coreapi.editorial.local.MatchupAssessment;
import java.util.List;
import java.util.Map;

/** Finite language shared with future selectors. No free text is accepted for public realization. */
public record ClaimSelection(ClaimSelector.SelectorIdentity selector, ClaimDocument document,
                             List<MatchupAssessment.Candidate> candidates, List<Decision> decisions) {
    public enum Kind { MATCHUP, LIMITATION, WINDOW_LIMITATION }
    public enum Predicate { SIGNAL_PROFILE, COVERAGE_LIMIT, SAMPLE_LIMIT, SIGN_VARIATION_LIMIT, LIMITED_SCOPE, POSITIVE_EPA_CONVERGENCE, ATTACK_DEFENSE_PROFILE, CONFLICTING_EPA_PROFILE,
        NO_DATA, PARTIAL_DATA, HISTORICAL_ONLY, SMALL_SAMPLE, LIMITED_WINDOW, UNEVEN_WINDOWS, MIXED_SIGNALS }
    public enum Period { CURRENT, HISTORICAL, NONE }
    public enum Role { OPPORTUNITY, LIMITATION }
    public enum Relation { DIRECT_CONFLICT, INDEPENDENT_OPPORTUNITY, INTERNAL_LIMITATION, ADDITIONAL_RESTRICTION }
    public enum Reason { PRIMARY, EQUAL_ALTERNATIVE, LOWER_COVERAGE, FOUNDATION_COVERAGE_POLICY,
        PROFILE_BEHIND_OPPORTUNITY, DIRECT_OBJECTION, NO_DIRECT_OBJECTION, OPPONENT_OPPORTUNITY,
        FACTUAL_LIMITATION, PRESERVED_IN_VERDICT, UNPAIRABLE, INTERNAL_RESTRICTION, DISTINCT_RESTRICTION,
        GENERAL_REDUNDANT, GENERAL_ADDS_INFORMATION, GROUPED_BY_TEAM }
    public record Decision(String candidateId, Reason reason) { }
    public record Claim(@JsonProperty("claim_id") String id, Kind type, String subject, Predicate predicate,
                        Period period, @JsonProperty("evidence_ids") List<String> evidenceIds, Role role,
                        @com.fasterxml.jackson.annotation.JsonInclude(com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL)
                        SignalDimensions signals) {
        public Claim(String id, Kind type, String subject, Predicate predicate, Period period, List<String> evidenceIds, Role role) {
            this(id, type, subject, predicate, period, evidenceIds, role, null);
        }
    }
    public record Link(String from, String to, Relation relation) { }
    public enum GroupReason { GENERAL_SAME_SIGNAL_AND_COVERAGE }
    public record Grouping(String candidateId, List<String> representedBy, GroupReason reason) { }
    public record ClaimDocument(@JsonProperty("contract_version") int version,
                                @JsonProperty("thesis_team") String thesisTeam, String verdict,
                                List<Claim> claims, Map<String, List<String>> sections, List<Link> links,
                                @com.fasterxml.jackson.annotation.JsonInclude(com.fasterxml.jackson.annotation.JsonInclude.Include.NON_EMPTY)
                                List<Grouping> groupings) {
        public ClaimDocument(int version, String thesisTeam, String verdict, List<Claim> claims,
                             Map<String, List<String>> sections, List<Link> links) {
            this(version, thesisTeam, verdict, claims, sections, links, List.of());
        }
    }
}
