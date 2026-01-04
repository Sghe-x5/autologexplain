import DatePicker from "@/features/DatePicker/DatePicker";
import "./App.css";
import React from "react";

function App() {
  const [date, setDate] = React.useState<Date | undefined>(undefined);
  return (<>
    <DatePicker date={date} setDate={setDate}></DatePicker>
  </>);
}

export default App;
