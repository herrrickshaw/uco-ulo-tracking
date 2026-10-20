import { useEffect, useState } from "react";

export default function useLoad(...fetchers) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    Promise.all(fetchers.map((f) => f())).then(setData).catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { data, error };
}
