# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "numpy==2.2.3",
#     "plotly==6.0.0",
#     "polars==1.23.0",
#     "scipy==1.15.2",
# ]
# ///

import marimo

__generated_with = "0.11.20"
app = marimo.App(width="medium")


@app.cell
def _():
    import numpy as np
    import polars as pl
    import plotly.express as px
    import plotly.graph_objects as go
    import plotly.io as pio

    from scipy.stats import gaussian_kde

    from datetime import datetime, date
    from functools import lru_cache
    from functools import partial

    import marimo as mo

    pio.templates.default = "simple_white"
    return (
        date,
        datetime,
        gaussian_kde,
        go,
        lru_cache,
        mo,
        np,
        partial,
        pio,
        pl,
        px,
    )


@app.cell
def _(gaussian_kde, np, partial, pl):
    def get_kde(
        arr: np.array, *, normalize: bool = True, eval_points: np.array = None
    ) -> np.array:
        """
        Given an array of data points, return the kde evaluated at the eval_points.

        Parameters:
        -----------
        arr : np.array
            The data points to fit the kde on.
        normalize : bool
            Normalize the kde.
        eval_points : np.array
            The points to evaluate the kde on.

        Returns:
        --------
        np.array
            The evaluated kde values at the specified points.
        """
        try:
            kde = gaussian_kde(arr)
            kde_points = kde.evaluate(eval_points)
            if normalize:
                kde_points = kde_points / kde_points.max()
            return kde_points
        except Exception:
            return np.array([0])


    def get_chunks(
        df: pl.DataFrame,
        *,
        ts_col: str,
        period: str,
        feature_col: str,
        normalize: bool = True,
        eval_points: np.array = None,
        group_by=None,
    ) -> pl.DataFrame:
        """
        Get chunks in one dimension of the data.
        For each group within a chunk create kde's.

        Parameters:
        -----------
        df : pl.DataFrame
            The input DataFrame.
        ts_col : str
            The timestamp column used for chunking.
        period : str
            The period for chunking.
        feature_col : str
            The column to calculate KDE on.
        normalize : bool
            Normalize the KDE.
        eval_points : np.array
            The points to evaluate the KDE on.
        group_by : Optional[str]
            The column to group by.

        Returns:
        --------
        list[pl.DataFrame]
            The DataFrame chunks with KDE results and additional metadata.
        """
        df_chunked = (
            df.group_by_dynamic(
                ts_col,
                every=period,
                group_by=group_by,
            )
            .agg(
                pl.col(feature_col),
            )
            .with_columns(
                kde=pl.col(feature_col).map_elements(
                    partial(get_kde, normalize=normalize, eval_points=eval_points),
                    return_dtype=pl.List(pl.Float32),
                ),
                eval_points=pl.lit(list(eval_points)),
                chunk_index=pl.cum_count(ts_col).over(
                    group_by,
                ),
                chunk_label=pl.col(ts_col).dt.strftime("%Y-%m"),
                group_index=pl.cum_count(ts_col).over(ts_col),
                group_key=pl.lit(group_by),
                group_value=pl.col(group_by)
                if group_by is not None
                else pl.lit(None),
            )
            .drop(feature_col)
            .sort(ts_col)
        )

        return df_chunked.partition_by(ts_col)
    return get_chunks, get_kde


@app.cell
def _(mo):
    mo.md(
        """
        # Univariate drift detection by target.

        The data consists of a single feature f1, a target and a timeseries column ts.
        """
    )
    return


@app.cell
def _(date, lru_cache, np, pl):
    @lru_cache(maxsize=10)
    def get_data(
        *,
        start: date,
        end: date,
        sampling_rate: str = "60s",
    ) -> pl.DataFrame:
        """
        Generate a time series data frame between specified start and end dates with a given sampling rate.

        Args:
        start (date): The start date of the data range.
        end (date): The end date of the data range.
        sampling_rate (str): The sampling rate as a string, default is "60s" (60 seconds).

        Returns:
        pl.DataFrame: A DataFrame with columns 'ts' for timestamps, 'f_1' for a feature influenced by time, and 'target' as a boolean series.
        """
        date_range = pl.datetime_range(
            start, end, interval=sampling_rate, eager=True
        )

        return pl.DataFrame(
            {
                "ts": date_range,
                "f_1": np.random.normal(0, 1, len(date_range)),
                "target": np.sin(np.linspace(0, 12 * np.pi, len(date_range))) >= 0,
            }
        ).with_columns(
            f_1=pl.col("f_1")
            + 12 * np.sin(pl.col("ts").dt.month() * 2 * np.pi / 12),
        )
    return (get_data,)


@app.cell
def _(mo):
    mo.md("""## Visualized chunks""")
    return


@app.cell
def _(df, mo):
    mo.md(
        f"""
        The data has {df.height} rows.
        """
    )
    return


@app.cell
def _(date, mo):
    date_range = mo.ui.date_range(
        date(2020, 1, 1),
        date(2025, 1, 1),
        label="Date range",
    )
    sampling_rate = mo.ui.slider(60, 60 * 60, 10, 1800, label="Sampling Rate")
    interval = mo.ui.slider(1, 12, 1, 6)
    kde_eval_points = mo.ui.slider(30, 100, 5, 50)
    group_by_target = mo.ui.checkbox(True)
    mo.vstack(
        [
            date_range,
            sampling_rate,
            mo.md(f"Chunk timestamps by {interval} months."),
            mo.md(f"Within each chunk, group by target ?: {group_by_target}"),
            mo.md(f"Sample the kde with {kde_eval_points} points."),
        ]
    )
    return (
        date_range,
        group_by_target,
        interval,
        kde_eval_points,
        sampling_rate,
    )


@app.cell
def _(date_range, get_data, sampling_rate):
    df = get_data(
        start=date_range.value[0],
        end=date_range.value[1],
        sampling_rate=f"{sampling_rate.value}s",
    )
    return (df,)


@app.cell
def _(df, get_chunks, group_by_target, interval, kde_eval_points, np):
    chunks = get_chunks(
        df,
        ts_col="ts",
        period=f"{interval.value}mo",
        group_by="target" if group_by_target.value else None,
        feature_col="f_1",
        normalize=True,
        eval_points=np.linspace(-20, 20, kde_eval_points.value),
    )
    return (chunks,)


@app.cell
def _(chunks, go, np):
    # Visualize data chunks and groups with vertical rectangles and scatter traces

    fig = go.Figure()

    colors = ["orange", "blue"]

    for chunk in chunks:
        # iterate over the groups inside the chunk
        for row in chunk.iter_rows(named=True):
            chunk_index = row["chunk_index"]
            chunk_name = row["chunk_label"]
            group_index = row["group_index"]
            group_value = row["group_value"]

            fig.add_vrect(
                x0=chunk_index,
                x1=chunk_index + 1,
                annotation_text=f"Chunk {chunk_index}",
                annotation_position="top left",
                fillcolor="purple" if chunk_index % 2 == 0 else "pink",
                opacity=0.05,
                line_width=0,
            )

            trace = go.Scatter(
                y=row["eval_points"],
                x=np.array(row["kde"]) + chunk_index,
                mode="lines",
                name=chunk_name,
                line=dict(width=2, color=colors[group_index - 1]),
                fill="tozeroy",
                legendgroup=group_index,
                legendgrouptitle={
                    "text": f"{row['group_key']}={row['group_value']}"
                }
                if group_value is not None
                else None,
            )

            fig.add_trace(trace)

    fig
    return (
        chunk,
        chunk_index,
        chunk_name,
        colors,
        fig,
        group_index,
        group_value,
        row,
        trace,
    )


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
