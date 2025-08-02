import DatePicker from "@/features/DatePicker/DatePicker";
import "./App.css";
import React from "react";

function App() {
  const [date, setDate] = React.useState<Date | undefined>(undefined);
  return (<>
    <DatePicker ></DatePicker>
  </>);
}

export default App;
