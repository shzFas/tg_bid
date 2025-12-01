import { Box } from "@mui/material";
import AppRouter from "./router";
import Sidebar from "./components/Sidebar";

export default function App() {
  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar />
      <Box sx={{ flexGrow: 1, p: 2 }}>
        <AppRouter />
      </Box>
    </Box>
  );
}
