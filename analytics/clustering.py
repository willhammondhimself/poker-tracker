"""
Villain Taxonomy - Unsupervised Learning with K-Means.

Uses PCA for dimensionality reduction and K-Means clustering
to automatically classify opponents into behavioral archetypes.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from typing import Optional
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans


# Archetype definitions based on centroid characteristics
ARCHETYPES = {
    'Nit': {
        'description': 'Tight-passive player, only plays premium hands',
        'color': '#3498DB',
        'exploit': 'Steal blinds aggressively, fold to their raises',
    },
    'TAG': {
        'description': 'Tight-aggressive, solid winning player',
        'color': '#27AE60',
        'exploit': 'Avoid marginal spots, 3-bet light occasionally',
    },
    'LAG': {
        'description': 'Loose-aggressive, wide range with aggression',
        'color': '#F39C12',
        'exploit': 'Trap with strong hands, call down lighter',
    },
    'Calling Station': {
        'description': 'Loose-passive, calls too much, rarely folds',
        'color': '#9B59B6',
        'exploit': 'Value bet relentlessly, never bluff',
    },
    'Maniac': {
        'description': 'Hyper-aggressive, bets and raises constantly',
        'color': '#E74C3C',
        'exploit': 'Let them hang themselves, trap with monsters',
    },
}


class VillainCluster:
    """
    K-Means clustering for opponent classification.

    Reduces player stats to 2 PCA components and clusters
    into distinct behavioral archetypes.
    """

    def __init__(
        self,
        player_stats: pd.DataFrame,
        min_hands: int = 50,
        n_clusters: int = 4,
    ):
        """
        Initialize the clustering model.

        Args:
            player_stats: DataFrame with columns: name, vpip, pfr, af, wtsd, hands_played
            min_hands: Minimum hands required for inclusion.
            n_clusters: Number of clusters (default 4).
        """
        self.raw_stats = player_stats
        self.min_hands = min_hands
        self.n_clusters = n_clusters

        self.filtered_stats = None
        self.scaled_features = None
        self.pca_coords = None
        self.labels = None
        self.cluster_stats = None
        self.cluster_names = None

        self._prepare_data()
        if self.filtered_stats is not None and len(self.filtered_stats) >= n_clusters:
            self._fit_model()

    def _prepare_data(self) -> None:
        """Filter and prepare data for clustering."""
        if self.raw_stats is None or len(self.raw_stats) == 0:
            return

        # Ensure required columns exist
        required = ['vpip', 'pfr', 'af', 'hands_played']
        if not all(col in self.raw_stats.columns for col in required):
            return

        # Filter by minimum hands
        self.filtered_stats = self.raw_stats[
            self.raw_stats['hands_played'] >= self.min_hands
        ].copy()

        if len(self.filtered_stats) < self.n_clusters:
            return

        # Add WTSD if not present (estimate from other stats)
        if 'wtsd' not in self.filtered_stats.columns:
            # Estimate: higher VPIP + lower AF = higher WTSD
            self.filtered_stats['wtsd'] = (
                self.filtered_stats['vpip'] * 0.5
                - self.filtered_stats['af'] * 5
                + 30
            ).clip(10, 60)

    def _fit_model(self) -> None:
        """Fit PCA and K-Means to the data."""
        # Feature matrix
        feature_cols = ['vpip', 'pfr', 'af', 'wtsd']
        available_cols = [c for c in feature_cols if c in self.filtered_stats.columns]

        if len(available_cols) < 2:
            return

        X = self.filtered_stats[available_cols].fillna(0).values

        # Standardize features
        scaler = StandardScaler()
        self.scaled_features = scaler.fit_transform(X)

        # PCA to 2 components
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(self.scaled_features)

        self.pca_coords = pd.DataFrame(
            pca_result,
            columns=['PC1', 'PC2'],
            index=self.filtered_stats.index,
        )
        self.pca_coords['name'] = self.filtered_stats['name'].values

        # K-Means clustering
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        self.labels = kmeans.fit_predict(self.scaled_features)
        self.pca_coords['cluster'] = self.labels

        # Copy stats to pca_coords for hover
        for col in available_cols:
            self.pca_coords[col] = self.filtered_stats[col].values

        # Analyze clusters and assign names
        self._analyze_clusters(available_cols)

    def _analyze_clusters(self, feature_cols: list) -> None:
        """Analyze cluster centroids and assign archetype names."""
        cluster_data = []

        for cluster_id in range(self.n_clusters):
            mask = self.labels == cluster_id
            cluster_stats = self.filtered_stats[mask][feature_cols].mean()

            cluster_data.append({
                'cluster': cluster_id,
                'count': mask.sum(),
                **cluster_stats.to_dict(),
            })

        self.cluster_stats = pd.DataFrame(cluster_data)

        # Assign archetype names based on centroid characteristics
        self.cluster_names = {}
        used_names = set()

        for _, row in self.cluster_stats.iterrows():
            cluster_id = int(row['cluster'])
            vpip = row.get('vpip', 25)
            pfr = row.get('pfr', 15)
            af = row.get('af', 2)

            # Classification logic
            if vpip < 20 and pfr < 15:
                name = 'Nit'
            elif vpip < 28 and pfr > 15 and af > 2:
                name = 'TAG'
            elif vpip > 35 and af > 3:
                name = 'Maniac' if af > 4 else 'LAG'
            elif vpip > 35 and af < 2:
                name = 'Calling Station'
            else:
                name = 'TAG'

            # Avoid duplicates
            if name in used_names:
                alternatives = ['LAG', 'Calling Station', 'Maniac', 'Nit', 'TAG']
                for alt in alternatives:
                    if alt not in used_names:
                        name = alt
                        break

            self.cluster_names[cluster_id] = name
            used_names.add(name)

        # Add names to cluster_stats
        self.cluster_stats['archetype'] = self.cluster_stats['cluster'].map(
            self.cluster_names
        )

        # Add to pca_coords
        self.pca_coords['archetype'] = self.pca_coords['cluster'].map(
            self.cluster_names
        )

    def get_player_archetype(self, player_name: str) -> Optional[str]:
        """Get the archetype for a specific player."""
        if self.pca_coords is None:
            return None

        match = self.pca_coords[self.pca_coords['name'] == player_name]
        if len(match) > 0:
            return match.iloc[0]['archetype']
        return None


def render_cluster_chart(
    player_stats: pd.DataFrame,
    title: str = "Villain Population Analysis (PCA + K-Means)",
) -> Optional[VillainCluster]:
    """
    Render the PCA/K-Means cluster visualization.

    Args:
        player_stats: DataFrame with player statistics.
        title: Chart title.

    Returns:
        VillainCluster instance or None if insufficient data.
    """
    if player_stats is None or len(player_stats) < 4:
        st.warning("Need at least 4 opponents with 50+ hands for clustering.")
        return None

    # Fit model
    model = VillainCluster(player_stats)

    if model.pca_coords is None or len(model.pca_coords) < 4:
        st.warning("Insufficient data after filtering. Need more opponents with 50+ hands.")
        return None

    # Create figure
    fig = go.Figure()

    # Add scatter points by cluster
    for archetype, info in ARCHETYPES.items():
        mask = model.pca_coords['archetype'] == archetype
        if not mask.any():
            continue

        subset = model.pca_coords[mask]

        # Build hover text
        hover_text = []
        for _, row in subset.iterrows():
            text = (
                f"<b>{row['name']}</b><br>"
                f"VPIP: {row.get('vpip', 0):.1f}%<br>"
                f"PFR: {row.get('pfr', 0):.1f}%<br>"
                f"AF: {row.get('af', 0):.2f}<br>"
                f"Archetype: {archetype}"
            )
            hover_text.append(text)

        fig.add_trace(go.Scatter(
            x=subset['PC1'],
            y=subset['PC2'],
            mode='markers+text',
            name=archetype,
            marker=dict(
                size=12,
                color=info['color'],
                line=dict(width=1, color='white'),
            ),
            text=subset['name'],
            textposition='top center',
            textfont=dict(size=9, color='#888'),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_text,
        ))

    # Style
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#fff')),
        xaxis_title='Principal Component 1',
        yaxis_title='Principal Component 2',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True,
        legend=dict(
            title='Archetype',
            orientation='v',
            yanchor='top',
            y=0.99,
            xanchor='left',
            x=1.02,
        ),
    )

    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')

    st.plotly_chart(fig, use_container_width=True)

    return model
