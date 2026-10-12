from odoo import fields, models
from odoo.exceptions import UserError


class NmeDocumentCancel(models.TransientModel):
    """Cancel any Nusantara ERP document with a mandatory reason.

    The wizard is generic: it works on every model inheriting
    ``nme.document.mixin`` and delegates the actual cancellation (and its
    business checks) to ``_cancel_with_reason`` of that model.
    """

    _name = "nme.document.cancel"
    _description = "Cancel Document"

    res_model = fields.Char(string="Document Model", required=True)
    res_ids = fields.Json(string="Documents", required=True)
    reason = fields.Text(required=True)

    def action_confirm(self):
        self.ensure_one()
        if self.res_model not in self.env or not issubclass(
            type(self.env[self.res_model]), self.pool["nme.document.mixin"]
        ):
            raise UserError(
                self.env._("Only Nusantara ERP documents can be cancelled here.")
            )
        documents = self.env[self.res_model].browse(self.res_ids).exists()
        documents._cancel_with_reason(self.reason)
        return {"type": "ir.actions.act_window_close"}
