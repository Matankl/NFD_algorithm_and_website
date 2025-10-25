from typing import Dict, Hashable, Iterable, Optional, Tuple, List
from math import inf


def is_EF11(
        instance: "Instance",
        bundles: Dict[Hashable, Iterable[Hashable]],
) -> dict:
    """
    Return detailed information about EF[1,1] allocation status.

    Returns a dictionary containing:
    - 'is_ef11': bool - whether allocation satisfies EF[1,1]
    - 'violating_pair': tuple or None - (envious_agent, envied_agent) if violation exists
    - 'swap_pairs': dict - for each agent, the item pairs that can eliminate their envy
    - 'bundle_values': dict - total values of each bundle from each agent's perspective

    Parameters
    ----------
    instance : Instance
        The instance that supplies all valuations and (optionally) item categories
    bundles : dict(agent -> iterable(item))
        The final allocation
    """
    agents = list(bundles.keys())
    A, B = agents[0], agents[1]  # exactly two agents supported

    # ---------- Helper: category of an item ----------
    if getattr(instance, "item_categories", None) is None:
        cat_of = lambda item: None
    else:
        item_cat = instance.item_categories
        cat_of = lambda item: item_cat[item]

    # ---------- Pre-compute per agent ----------
    wost_chore_in_cat_eyes_of_self = {a: {} for a in agents}
    best_good_in_cat_eyes_of_other = {a: {} for a in agents}

    # Track which specific items are the worst chores and best goods
    wost_chore_item = {a: {} for a in agents}
    best_good_item = {a: {} for a in agents}

    total_value_eyes_of_A = {}
    total_value_eyes_of_B = {}

    # Agent A perspective
    total_A_for_itself = 0.0
    total_A_for_other = 0.0
    for ag, Bundel in bundles.items():
        for item in Bundel:
            v = instance.agent_item_value(A, item)
            c = cat_of(item)
            if item in bundles[A]:
                total_A_for_itself += v
            else:
                total_A_for_other += v

            if v < 0 and item in bundles[A]:  # chore for A in A's bundle
                d = wost_chore_in_cat_eyes_of_self[A].get(c, inf)
                if v < d:
                    wost_chore_in_cat_eyes_of_self[A][c] = v
                    wost_chore_item[A][c] = item
            elif v > 0 and item not in bundles[A]:  # good for A in B's bundle
                d = best_good_in_cat_eyes_of_other[B].get(c, -inf)
                if v > d:
                    best_good_in_cat_eyes_of_other[B][c] = v
                    best_good_item[B][c] = item

    total_value_eyes_of_A[A] = total_A_for_itself
    total_value_eyes_of_A[B] = total_A_for_other

    # Agent B perspective
    total_B_for_itself = 0.0
    total_B_for_other = 0.0
    for ag, Bundel in bundles.items():
        for item in Bundel:
            v = instance.agent_item_value(B, item)
            c = cat_of(item)
            if item in bundles[B]:
                total_B_for_itself += v
            else:
                total_B_for_other += v

            if v < 0 and item in bundles[B]:  # chore for B in B's bundle
                d = wost_chore_in_cat_eyes_of_self[B].get(c, inf)
                if v < d:
                    wost_chore_in_cat_eyes_of_self[B][c] = v
                    wost_chore_item[B][c] = item
            elif v > 0 and item not in bundles[B]:  # good for B in A's bundle
                d = best_good_in_cat_eyes_of_other[A].get(c, -inf)
                if v > d:
                    best_good_in_cat_eyes_of_other[A][c] = v
                    best_good_item[A][c] = item

    total_value_eyes_of_B[B] = total_B_for_itself
    total_value_eyes_of_B[A] = total_B_for_other

    # ---------- Prepare result dictionary ----------
    result = {
        'is_ef11': True,
        'violating_pair': None,
        'swap_pairs': {A: [], B: []},
        'bundle_values': {
            A: {
                'own_bundle_value': total_value_eyes_of_A[A],
                'other_bundle_value': total_value_eyes_of_A[B],
                'gap': total_value_eyes_of_A[A] - total_value_eyes_of_A[B]
            },
            B: {
                'own_bundle_value': total_value_eyes_of_B[B],
                'other_bundle_value': total_value_eyes_of_B[A],
                'gap': total_value_eyes_of_B[B] - total_value_eyes_of_B[A]
            }
        }
    }

    # ---------- Check for envy and find swap pairs ----------

    # Check if A envies B
    gap = total_value_eyes_of_A[A] - total_value_eyes_of_A[B]
    if gap < 0:  # A envies B
        needed = -gap
        candidate_categories = set(wost_chore_in_cat_eyes_of_self[A]).intersection(
            best_good_in_cat_eyes_of_other[B]
        )

        envy_eliminated = False
        for c in candidate_categories:
            chore = wost_chore_item[A][c]
            good = best_good_item[B][c]
            chore_val = wost_chore_in_cat_eyes_of_self[A][c]
            good_val = best_good_in_cat_eyes_of_other[B][c]
            gain = -chore_val + good_val

            result['swap_pairs'][A].append({
                'category': c,
                'remove_from_own': chore,
                'remove_from_other': good,
                'chore_value': chore_val,
                'good_value': good_val,
                'total_gain': gain,
                'eliminates_envy': gain >= needed
            })

            if gain >= needed:
                envy_eliminated = True

        if not envy_eliminated:
            result['is_ef11'] = False
            result['violating_pair'] = (A, B)
            return result

    # Check if B envies A
    gap = total_value_eyes_of_B[B] - total_value_eyes_of_B[A]
    if gap < 0:  # B envies A
        needed = -gap
        candidate_categories = set(wost_chore_in_cat_eyes_of_self[B]).intersection(
            best_good_in_cat_eyes_of_other[A]
        )

        envy_eliminated = False
        for c in candidate_categories:
            chore = wost_chore_item[B][c]
            good = best_good_item[A][c]
            chore_val = wost_chore_in_cat_eyes_of_self[B][c]
            good_val = best_good_in_cat_eyes_of_other[A][c]
            gain = -chore_val + good_val

            result['swap_pairs'][B].append({
                'category': c,
                'remove_from_own': chore,
                'remove_from_other': good,
                'chore_value': chore_val,
                'good_value': good_val,
                'total_gain': gain,
                'eliminates_envy': gain >= needed
            })

            if gain >= needed:
                envy_eliminated = True

        if not envy_eliminated:
            result['is_ef11'] = False
            result['violating_pair'] = (B, A)
            return result

    return result