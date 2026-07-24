import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render_rank_history(term: str, dates, positions) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, positions, marker="o", linewidth=2)
    ax.invert_yaxis()
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
