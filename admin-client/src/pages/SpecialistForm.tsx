// src/components/specialists/SpecialistForm.tsx
import { useState, useEffect } from "react";
import {
  Dialog, DialogTitle, DialogContent,
  TextField, Button, FormGroup, FormControlLabel,
  Checkbox, Typography
} from "@mui/material";
import {
  createSpecialist,
  updateSpecialist,
  approveSpecialist
} from "../api/specialists";

interface Props {
  open: boolean;
  onClose: () => void;
  editing?: any;      // если есть → режим редактирования
  reload: () => void; // обновление таблицы после сохранения
}

const ALL_SPECS = ["ACCOUNTING", "LAW", "EGOV"];

export default function SpecialistForm({ open, onClose, editing, reload }: Props) {
  const [form, setForm] = useState({
    name: "",
    phone: "",
    tg_id: "",
    username: "",
    specializations: [] as string[]
  });

  // ⚡ Автоматически заполняет форму при редактировании
  useEffect(() => {
    if (editing) {
      setForm({
        name: editing.name,
        phone: editing.phone,
        tg_id: editing?.tg_id,
        username: editing.username,
        specializations: editing.specializations || []
      });
    } else {
      setForm({ name: "", phone: "", tg_id: "", username: "", specializations: [] });
    }
  }, [editing, open]); // при изменении editing или открытии — обновляем

  const toggleSpec = (spec: string) => {
    setForm(prev => ({
      ...prev,
      specializations: prev.specializations.includes(spec)
        ? prev.specializations.filter(s => s !== spec)
        : [...prev.specializations, spec]
    }));
  };

  const handleSave = async () => {
    if (editing) {
      await updateSpecialist(editing.id, form);
    } else {
      await createSpecialist(form);
    }
    reload();
    onClose();
  };

  const handleApprove = async () => {
    await approveSpecialist(editing!.id);
    reload();
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>
        {editing ? "Редактировать специалиста" : "Новый специалист"}
      </DialogTitle>

      <DialogContent sx={{ mt: 1 }}>
        <TextField
          fullWidth
          label="Имя"
          value={form.name}
          onChange={e => setForm({ ...form, name: e.target.value })}
          margin="dense"
        />

        <TextField
          fullWidth
          label="Telegram ID (tg_id)"
          value={form.tg_id}
          onChange={e => setForm({ ...form, tg_id: e.target.value })}
          margin="dense"
        />

        <TextField
          fullWidth
          label="Username Telegram (если есть)"
          value={form.username}
          onChange={e => setForm({ ...form, username: e.target.value })}
          margin="dense"
        />

        <TextField
          fullWidth
          label="Телефон"
          value={form.phone}
          onChange={e => setForm({ ...form, phone: e.target.value })}
          margin="dense"
        />

        <Typography sx={{ mt: 2 }}>Специализации:</Typography>
        <FormGroup>
          {ALL_SPECS.map(spec => (
            <FormControlLabel
              key={spec}
              control={
                <Checkbox
                  checked={form.specializations.includes(spec)}
                  onChange={() => toggleSpec(spec)}
                />
              }
              label={spec}
            />
          ))}
        </FormGroup>

        {/* Если режим редактирования — показываем статус / апрув */}
        {editing && (
          <>
            <Typography sx={{ mt: 2 }}>
              Статус: <b>{editing.is_approved ? "✔ ОДОБРЕН" : "⏳ НЕ ОДОБРЕН"}</b>
            </Typography>

            {!editing.is_approved && (
              <Button
                fullWidth
                color="success"
                variant="contained"
                sx={{ mt: 2 }}
                onClick={handleApprove}
              >
                ОДОБРИТЬ
              </Button>
            )}
          </>
        )}

        <Button
          fullWidth
          variant="contained"
          sx={{ mt: 2 }}
          onClick={handleSave}
        >
          Сохранить
        </Button>
      </DialogContent>
    </Dialog>
  );
}
