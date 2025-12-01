import { createContext, useContext, useState } from "react";
import { Snackbar, Alert } from "@mui/material";

interface SnackbarContextType {
  showMessage: (message: string, severity?: "error" | "success" | "info" | "warning") => void;
}

const SnackbarContext = createContext<SnackbarContextType>({
  showMessage: () => {},
});

export const useSnackbar = () => useContext(SnackbarContext);

export function SnackbarProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [severity, setSeverity] = useState<"error" | "success" | "info" | "warning">("info");

  const showMessage = (msg: string, sev: any = "info") => {
    setMessage(msg);
    setSeverity(sev);
    setOpen(true);
  };

  return (
    <SnackbarContext.Provider value={{ showMessage }}>
      {children}

      <Snackbar 
        open={open}
        autoHideDuration={3000}
        onClose={() => setOpen(false)}
      >
        <Alert severity={severity} onClose={() => setOpen(false)} variant="filled">
          {message}
        </Alert>
      </Snackbar>
    </SnackbarContext.Provider>
  );
}
