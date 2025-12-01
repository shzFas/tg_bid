// src/components/specialists/SpecialistsList.tsx
import { useEffect, useState } from "react";
import { getAllSpecialists } from "../api/specialists";
import { Box, Button, Typography } from "@mui/material";
import SpecialistsTable from "./SpecialistsTable";
import SpecialistForm from "./SpecialistForm";

export default function SpecialistsList() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [data, setData] = useState<any[]>([]);   // <--- как ты предложил

  useEffect(() => {
    getAllSpecialists().then((res) => {
      if (Array.isArray(res)) setData(res); // защита
      else setData([]);
    });
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
        specialists={data}    // <--- передаем сюда!
        refresh={() => getAllSpecialists().then(setData)} // обновляем
        onEdit={(s: any) => { setEditing(s); setOpen(true); }}
      />

      {/* Диалог */}
      <SpecialistForm
        open={open}
        onClose={() => setOpen(false)}
        editing={editing}
        reload={() => getAllSpecialists().then(setData)} // перезагрузка
      />
    </Box>
  );
}
