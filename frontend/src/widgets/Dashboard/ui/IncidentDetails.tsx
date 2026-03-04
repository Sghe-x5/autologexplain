import { useGetIncidentQuery } from "@/api";
export const IncidentDetails = ({ incidentId, onBack }: { incidentId: string; onBack: () => void }) => {
  const { data } = useGetIncidentQuery(incidentId);
  return <section><button onClick={onBack}>Back</button><h2>{data?.title ?? incidentId}</h2></section>;
};
