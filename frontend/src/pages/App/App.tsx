import { useEffect, useState } from "react";
import { FILTER_URL } from "@/consts/api.const";

type Service = { service: string; environments: string[] };
type Product = { product: string; services: Service[] };

export default function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selected, setSelected] = useState("");
  const [environment, setEnvironment] = useState("");
  const [error, setError] = useState(false);
  useEffect(() => {
    fetch(FILTER_URL)
      .then(async response => {
        if (!response.ok) throw new Error("Could not load filters");
        return await response.json() as Product[];
      })
      .then(setProducts)
      .catch(() => setError(true));
  }, []);
  const services = products.flatMap(p => p.services.map(s => ({ ...s, key: p.product + "/" + s.service })));
  return (
    <main data-test-id="app-root">
      <h1>Log filters</h1>
      {error && <p role="alert">Could not load log filters.</p>}
      <label>Service
        <select value={selected} onChange={e => { setSelected(e.target.value); setEnvironment(""); }}>
          <option value="">Choose a service</option>
          {services.map(s => <option key={s.key} value={s.key}>{s.key}</option>)}
        </select>
      </label>
      <label>Environment
        <select value={environment} onChange={e => setEnvironment(e.target.value)}>
          <option value="">Choose an environment</option>
          {services.find(s => s.key === selected)?.environments.map(e => <option key={e}>{e}</option>)}
        </select>
      </label>
      <label>Start <input type="datetime-local" /></label>
      <label>End <input type="datetime-local" /></label>
    </main>
  );
}
