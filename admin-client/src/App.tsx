import { Box } from "@mui/material";
import AppRouter from "./router";
import Sidebar from "./components/Sidebar";
import { SnackbarProvider } from "./components/SnackbarProvider";

export default function App() {
  return (
    <SnackbarProvider>
      <Box sx={{ display: "flex" }}>
        <Sidebar />
        <Box sx={{ flexGrow: 1, p: 2 }}>
          <AppRouter />
        </Box>
      </Box>
    </SnackbarProvider>
  );
}
