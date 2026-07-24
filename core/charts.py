import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render_rank_history(term: str, dates, positions) -> io.BytesIO:
    """
    dates: list[datetime], positions: list[int|None] (None = not ranked, plotted as a gap)
    Returns a PNG in a BytesIO buffer, ready to send via bot.send_photo.
    """
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, positions, marker="o", linewidth=2)
    ax.invert_yaxis()  # position 1 should be at the top
    ax.set_title(f'Ranking history: "{term}"')
    ax.set_xlabel("Date")
    ax.set_ylabel("Position")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
