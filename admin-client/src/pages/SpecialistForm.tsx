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
import { useSnackbar } from "../components/SnackbarProvider";

interface Props {
  open: boolean;
  onClose: () => void;
  editing?: any;
  reload: () => void;
}

const ALL_SPECS = ["ACCOUNTING", "LAW", "EGOV"];

export default function SpecialistForm({ open, onClose, editing, reload }: Props) {
  const { showMessage } = useSnackbar();

  const [form, setForm] = useState({
    name: "",
    phone: "",
    tg_id: "",
    username: "",
    specializations: [] as string[],
  });

  // Заполнение формы при открытии
  useEffect(() => {
    if (editing) {
      setForm({
        name: editing.name,
        phone: editing.phone,
        tg_id: editing.tg_id,
        username: editing.username,
        specializations: editing.specializations || [],
      });
    } else {
      setForm({
        name: "",
        phone: "",
        tg_id: "",
        username: "",
        specializations: [],
      });
    }
  }, [editing, open]);

  const toggleSpec = (spec: string) => {
    setForm((prev) => ({
      ...prev,
      specializations: prev.specializations.includes(spec)
        ? prev.specializations.filter((s) => s !== spec)
        : [...prev.specializations, spec],
    }));
  };

  // SAVE specialist
  const handleSave = async () => {
    try {
      if (editing) {
        await updateSpecialist(editing.id, form);
        showMessage("Специалист обновлён!", "success");
      } else {
        await createSpecialist(form);
        showMessage("Специалист создан!", "success");
      }

      reload();
      onClose();
    } catch (err: any) {
      showMessage(err.message, "error");
    }
  };

  // APPROVE specialist
  const handleApprove = async () => {
    try {
      await approveSpecialist(editing!.id);
      showMessage("Специалист успешно одобрен!", "success");

      reload();
      onClose();
    } catch (err: any) {
      showMessage(err.message, "error");
    }
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
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          margin="dense"
        />

        <TextField
          fullWidth
          label="Telegram ID (tg_id)"
          value={form.tg_id}
          onChange={(e) => setForm({ ...form, tg_id: e.target.value })}
          margin="dense"
        />

        <TextField
          fullWidth
          label="Username Telegram"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          margin="dense"
        />

        <TextField
          fullWidth
          label="Телефон"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
          margin="dense"
        />

        <Typography sx={{ mt: 2 }}>Специализации:</Typography>

        <FormGroup>
          {ALL_SPECS.map((spec) => (
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

        {/* Статус одобрения */}
        {editing && (
          <>
            <Typography sx={{ mt: 2 }}>
              Статус:{" "}
              <b>{editing.is_approved ? "✔ ОДОБРЕН" : "⏳ НЕ ОДОБРЕН"}</b>
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
