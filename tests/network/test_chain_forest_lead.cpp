// Unit gates for the lead arcs of the chain's forest growth (network/ar/ArcGraph.hpp, ForestRules::lead_rank): suite
// ChainForestLead.  A cascade's third band grown on its pair's forest (network.ring_fix.cascade_tree) ranks the pair's
// tree edges 1 and the pair's held links 2 and 3; the walk takes them before any incumbent, held or new edge.
//
//   - a rank-1 arc comes before the incumbent, and the walk then takes one edge at a time;
//   - rank 2 before rank 3, both after rank 1;
//   - a lead edge on an incumbent arc reads as kept;
//   - on random graphs the result spans the component and holds every arc of a rank-1 forest.

#include "network/ar/ArcGraph.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <numeric>
#include <random>
#include <set>
#include <vector>

namespace GnssProcessor {
namespace {

using namespace arcgraph;

ArcFamily oneBand() { return ArcFamily{System::GPS, {*SignalId::fromObsCode(System::GPS, "L5Q")}}; }

ArcRow row(int station, int prn) {
    ArcRow r;
    r.station = StationId{station};
    r.sat     = SatId{System::GPS, prn};
    r.present = 1;
    return r;
}

ArcGraph graphOf(int n_sta, int n_sat, const std::vector<ArcRow>& rows) {
    std::vector<StationId> so;
    for (int s = 0; s < n_sta; ++s) so.push_back(StationId{s});
    std::vector<SatId> ko;
    for (int k = 1; k <= n_sat; ++k) ko.push_back(SatId{System::GPS, k});
    return buildArcGraph(oneBand(), so, ko, rows);
}

/// Lead ranks over a graph's arcs: rank of each listed arc, 0 elsewhere.
std::vector<char> ranks(const ArcGraph& g, const std::vector<std::pair<int, char>>& arc_rank) {
    std::vector<char> r(g.rows.size(), 0);
    for (const auto& [a, k] : arc_rank) r[static_cast<std::size_t>(a)] = k;
    return r;
}

TEST(ChainForestLead, ARankOneArcComesBeforeTheIncumbent) {
    // A (root) and B track x and y; B's incumbent is (B, y).  As built: A takes x and y, B joins through its incumbent.
    // With (B, x) at rank 1: A takes x (its first new edge, one at a time), B joins through (B, x) before its
    // incumbent, and y then joins through the incumbent (B, y), so (A, y) is not taken.
    const ArcGraph g = graphOf(2, 2, {row(0, 1), row(0, 2), row(1, 1), row(1, 2)});
    const Component c = arcComponents(g, 1, {}).at(0);
    const std::vector<int> incumbent{arcIndex(g, 1, 1)};
    ForestRules rules;
    const SpanningForest plain = growChainForest(g, c, {stationVertex(g, 0)}, incumbent, rules, {}, {});
    ASSERT_EQ(plain.edges.size(), 3u);
    EXPECT_EQ(plain.edges[0].arc, arcIndex(g, 0, 0));
    EXPECT_EQ(plain.edges[1].arc, arcIndex(g, 0, 1));
    EXPECT_EQ(plain.edges[2].arc, arcIndex(g, 1, 1));
    const std::vector<char> lead = ranks(g, {{arcIndex(g, 1, 0), 1}});
    rules.lead_rank = &lead;
    const SpanningForest f = growChainForest(g, c, {stationVertex(g, 0)}, incumbent, rules, {}, {});
    ASSERT_EQ(f.edges.size(), 3u);
    EXPECT_EQ(f.edges[0].arc, arcIndex(g, 0, 0));
    EXPECT_EQ(f.edges[0].lead, 0);
    EXPECT_EQ(f.edges[1].arc, arcIndex(g, 1, 0));
    EXPECT_EQ(f.edges[1].lead, 1);
    EXPECT_FALSE(f.edges[1].from_incumbent);
    EXPECT_EQ(f.edges[2].arc, arcIndex(g, 1, 1));
    EXPECT_TRUE(f.edges[2].from_incumbent);
    EXPECT_EQ(f.edges[2].lead, 0);
}

TEST(ChainForestLead, RankTwoComesBeforeRankThreeAndBothAfterRankOne) {
    // A (root) reaches x through its rank-1 arc; B and C each track x only, (B, x) at rank 3 and (C, x) at rank 2:
    // C joins before B.
    const ArcGraph g = graphOf(3, 1, {row(0, 1), row(1, 1), row(2, 1)});
    const Component c = arcComponents(g, 1, {}).at(0);
    const std::vector<char> lead = ranks(g, {{arcIndex(g, 0, 0), 1}, {arcIndex(g, 1, 0), 3}, {arcIndex(g, 2, 0), 2}});
    ForestRules rules;
    rules.lead_rank = &lead;
    const SpanningForest f = growChainForest(g, c, {stationVertex(g, 0)}, {}, rules, {}, {});
    ASSERT_EQ(f.edges.size(), 3u);
    EXPECT_EQ(f.edges[0].arc, arcIndex(g, 0, 0));
    EXPECT_EQ(f.edges[0].lead, 1);
    EXPECT_EQ(f.edges[1].arc, arcIndex(g, 2, 0));
    EXPECT_EQ(f.edges[1].lead, 2);
    EXPECT_EQ(f.edges[2].arc, arcIndex(g, 1, 0));
    EXPECT_EQ(f.edges[2].lead, 3);
}

TEST(ChainForestLead, ALeadEdgeOnAnIncumbentArcReadsAsKept) {
    const ArcGraph g = graphOf(2, 1, {row(0, 1), row(1, 1)});
    const Component c = arcComponents(g, 1, {}).at(0);
    const std::vector<int> incumbent{arcIndex(g, 0, 0), arcIndex(g, 1, 0)};
    const std::vector<char> lead = ranks(g, {{arcIndex(g, 1, 0), 1}});
    ForestRules rules;
    rules.lead_rank = &lead;
    const SpanningForest f = growChainForest(g, c, {stationVertex(g, 0)}, incumbent, rules, {}, {});
    ASSERT_EQ(f.edges.size(), 2u);
    EXPECT_EQ(f.edges[0].arc, arcIndex(g, 0, 0));   // the root's incumbent: no lead arc reaches x from A
    EXPECT_TRUE(f.edges[0].from_incumbent);
    EXPECT_EQ(f.edges[1].arc, arcIndex(g, 1, 0));
    EXPECT_EQ(f.edges[1].lead, 1);
    EXPECT_TRUE(f.edges[1].from_incumbent);
}

TEST(ChainForestLead, OnRandomGraphsTheForestSpansAndHoldsEveryArcOfARankOneForest) {
    std::mt19937 rng(20261116);
    for (int trial = 0; trial < 200; ++trial) {
        const int n_sta = std::uniform_int_distribution<int>(2, 8)(rng);
        const int n_sat = std::uniform_int_distribution<int>(2, 8)(rng);
        std::vector<ArcRow> rows;
        for (int s = 0; s < n_sta; ++s)
            for (int k = 1; k <= n_sat; ++k)
                if (std::uniform_real_distribution<double>(0.0, 1.0)(rng) < 0.7) rows.push_back(row(s, k));
        const ArcGraph g = graphOf(n_sta, n_sat, rows);
        const std::vector<Component> comps = arcComponents(g, 1, {});
        if (comps.empty()) continue;
        const Component& c = comps[0];
        // A rank-1 forest: the arcs a union-find accepts in a random order, each kept with probability 1/2; random
        // ranks 2 and 3 elsewhere, and a random incumbent.
        std::vector<int> order(g.rows.size());
        std::iota(order.begin(), order.end(), 0);
        std::shuffle(order.begin(), order.end(), rng);
        std::vector<int> parent(static_cast<std::size_t>(n_sta + n_sat));
        std::iota(parent.begin(), parent.end(), 0);
        const auto find = [&](int v) {
            while (parent[static_cast<std::size_t>(v)] != v) v = parent[static_cast<std::size_t>(v)];
            return v;
        };
        std::vector<char> lead(g.rows.size(), 0);
        std::vector<int> incumbent;
        for (int a : order) {
            const int u = stationVertex(g, g.row_station[static_cast<std::size_t>(a)]);
            const int v = satVertex(g, g.row_sat[static_cast<std::size_t>(a)]);
            const int coin = std::uniform_int_distribution<int>(0, 3)(rng);
            if (coin == 0 && find(u) != find(v)) {
                parent[static_cast<std::size_t>(find(u))] = find(v);
                lead[static_cast<std::size_t>(a)] = 1;
            } else if (coin == 1) {
                lead[static_cast<std::size_t>(a)] = static_cast<char>(std::uniform_int_distribution<int>(2, 3)(rng));
            } else if (coin == 2) {
                incumbent.push_back(a);
            }
        }
        ForestRules rules;
        rules.lead_rank = &lead;
        const int root = stationVertex(g, c.stations.front());
        const SpanningForest f = growChainForest(g, c, {root}, incumbent, rules, {}, {});
        const std::size_t n_vertices = c.stations.size() + c.sats.size();
        ASSERT_EQ(f.edges.size(), n_vertices - 1) << "trial " << trial;
        std::set<int> tree;
        for (const TreeEdge& e : f.edges) tree.insert(e.arc);
        ASSERT_EQ(tree.size(), f.edges.size()) << "trial " << trial;
        const std::set<int> in_comp_sta(c.stations.begin(), c.stations.end());
        for (std::size_t a = 0; a < g.rows.size(); ++a)
            if (lead[a] == 1 && in_comp_sta.count(g.row_station[a]) != 0)
                EXPECT_EQ(tree.count(static_cast<int>(a)), 1u) << "trial " << trial << ": rank-1 arc " << a << " left out";
    }
}

}  // namespace
}  // namespace GnssProcessor
