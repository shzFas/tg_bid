import { useEffect, useState } from "react";
import { getAllSpecialists } from "../api/specialists";
import { Box, Button, Typography } from "@mui/material";
import SpecialistsTable from "./SpecialistsTable";
import SpecialistForm from "./SpecialistForm";
import { Specialist } from "../types";
import { useSnackbar } from "../components/SnackbarProvider";

export default function SpecialistsList() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Specialist | null>(null);
  const [data, setData] = useState<Specialist[]>([]);
  const { showMessage } = useSnackbar();

  async function refreshData() {
    try {
      const res = await getAllSpecialists();
      if (Array.isArray(res)) {
        setData(res);
      } else {
        setData([]);
      }
    } catch (err: any) {
      showMessage(err.message, "error");
    }
  }

  useEffect(() => {
    refreshData();
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Список специалистов
      </Typography>

      <Button
        variant="contained"
        onClick={() => {
          setEditing(null);
          setOpen(true);
        }}
        sx={{ mb: 2 }}
      >
        ➕ Добавить специалиста
      </Button>

      {/* Таблица */}
      <SpecialistsTable
        specialists={data}
        refresh={refreshData}
        onEdit={(s: Specialist) => {
          setEditing(s);
          setOpen(true);
        }}
      />

      {/* Диалог */}
      <SpecialistForm
        open={open}
        onClose={() => setOpen(false)}
        editing={editing}
        reload={refreshData}
      />
    </Box>
  );
}
