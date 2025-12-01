import {
  Table, TableHead, TableRow, TableCell,
  TableBody, IconButton, Tooltip, Chip
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import CheckIcon from "@mui/icons-material/Check";
import {
  deleteSpecialist,
  approveSpecialist
} from "../api/specialists";
import { useSnackbar } from "../components/SnackbarProvider";

export default function SpecialistsTable({ specialists, refresh, onEdit }: any) {
  const { showMessage } = useSnackbar();

  const handleDelete = async (id: number) => {
    try {
      await deleteSpecialist(id);
      showMessage("Специалист удалён", "success");
      refresh();
    } catch (err: any) {
      showMessage(err.message, "error");
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await approveSpecialist(id);
      showMessage("Специалист одобрен!", "success");
      refresh();
    } catch (err: any) {
      showMessage(err.message, "error");
    }
  };

  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>ID</TableCell>
          <TableCell>Имя</TableCell>
          <TableCell>Телефон</TableCell>
          <TableCell>Специализации</TableCell>
          <TableCell>Одобрен?</TableCell>
          <TableCell>Действия</TableCell>
        </TableRow>
      </TableHead>

      <TableBody>
        {specialists.map((s: any) => (
          <TableRow key={s.id}>
            <TableCell>{s.id}</TableCell>
            <TableCell>{s.name}</TableCell>
            <TableCell>{s.phone}</TableCell>
            <TableCell>{s.specializations.join(", ")}</TableCell>

            <TableCell>
              <Chip
                label={s.is_approved ? "YES" : "NO"}
                color={s.is_approved ? "success" : "warning"}
              />
            </TableCell>

            <TableCell>
              {/* ОДОБРИТЬ */}
              {!s.is_approved && (
                <Tooltip title="Одобрить">
                  <IconButton onClick={() => handleApprove(s.id)}>
                    <CheckIcon color="success" />
                  </IconButton>
                </Tooltip>
              )}

              {/* РЕДАКТИРОВАНИЕ */}
              <Tooltip title="Редактировать">
                <IconButton onClick={() => onEdit(s)}>
                  <EditIcon />
                </IconButton>
              </Tooltip>

              {/* УДАЛЕНИЕ */}
              <Tooltip title="Удалить">
                <IconButton onClick={() => handleDelete(s.id)}>
                  <DeleteIcon color="error" />
                </IconButton>
              </Tooltip>
            </TableCell>

          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
