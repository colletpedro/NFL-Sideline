package com.nflsideline.coreapi.editorial;

/** Selection only. Implementations must not validate or realize their own output. */
public interface ClaimSelector {
    SelectorIdentity identity();
    ClaimSelection select(AnalysisContext context, EditorialParameters parameters);
    record SelectorIdentity(String name, String version) { }
}
