import numpy as np
from promptops.similarity import VectorDB
import tempfile
from time import time


def generate_data(samples: int, d: int, seed: int = 42) -> VectorDB:
    np.random.seed(seed)
    x = np.random.randn(samples, d)
    # l2-normalize
    x /= np.linalg.norm(x, axis=1, keepdims=True)

    content = [{"text": f"content {i}"} for i in range(samples)]

    db = VectorDB()
    db.vectors = x
    db.objects = content
    return db


def main():
    db = generate_data(10000, 1536)
    with tempfile.NamedTemporaryFile(suffix=".npz") as f:
        now = time()
        db.save(f.name)
        print(f"saved in {time() - now:.3f} seconds")
        now = time()
        db.load(f.name)
        print(f"loaded in {time() - now:.3f} seconds")

    # test search
    query = np.random.randn(1, 1536)
    query /= np.linalg.norm(query, axis=1, keepdims=True)
    now = time()
    results = db.search(query, k=10, min_similarity=0.0)
    print(f"searched in {time() - now:.3f} seconds")
    print(results)


if __name__ == "__main__":
    main()
