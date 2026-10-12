from odoo import api, fields, models
from odoo.exceptions import UserError


class NmeDocumentMixin(models.AbstractModel):
    """Lifecycle shared by every business document of Nusantara ERP.

    It provides:

    * numbering from an ``ir.sequence`` when the document is created;
    * a strict state machine: a document declares the allowed moves in
      ``_state_transitions`` and changes state only through ``_set_state``;
    * cancellation with a mandatory reason (see ``nme.document.cancel``);
    * chatter, activities and protection against deleting confirmed documents.

    The concrete model must define a ``state`` selection field.
    """

    _name = "nme.document.mixin"
    _description = "Nusantara ERP Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _check_company_auto = True

    # {from_state: {allowed target states}}, defined by each document.
    _state_transitions = {}
    # States in which a document may still be deleted.
    _unlink_allowed_states = ("draft", "cancel")

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        copy=False,
        index="trigram",
        default=lambda self: self.env._("New"),
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        index=True,
        tracking=True,
        check_company=True,
        domain=[("share", "=", False)],
        default=lambda self: self.env.user,
    )
    cancel_reason = fields.Text(readonly=True, copy=False)
    note = fields.Html(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        new_name = self.env._("New")
        for vals in vals_list:
            if vals.get("name", new_name) == new_name:
                vals["name"] = self._next_sequence_number(vals) or new_name
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        for document in self:
            if document.state not in self._unlink_allowed_states:
                raise UserError(
                    self.env._(
                        "%s cannot be deleted anymore. Cancel it instead.",
                        document.display_name,
                    )
                )

    def action_open_cancel_wizard(self):
        """Open the wizard asking why the documents are cancelled."""
        return {
            "name": self.env._("Cancel %s", self._description),
            "type": "ir.actions.act_window",
            "res_model": "nme.document.cancel",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_res_model": self._name, "default_res_ids": self.ids},
        }

    def action_cancel(self):
        """Cancel the documents. Documents override it to add their own checks."""
        self._set_state("cancel")
        return True

    def _get_sequence_code(self, vals):
        """Return the ``ir.sequence`` code used to number a new document."""
        return self._name

    def _next_sequence_number(self, vals):
        company_id = vals.get("company_id") or self.env.company.id
        return (
            self.env["ir.sequence"]
            .with_company(company_id)
            .next_by_code(self._get_sequence_code(vals))
        )

    def _set_state(self, new_state):
        """Move the documents to ``new_state`` if ``_state_transitions`` allows it."""
        labels = dict(self._fields["state"]._description_selection(self.env))
        for document in self:
            if new_state not in self._state_transitions.get(document.state, ()):
                raise UserError(
                    self.env._(
                        "%(document)s cannot go from %(old)s to %(new)s.",
                        document=document.display_name,
                        old=labels.get(document.state),
                        new=labels.get(new_state),
                    )
                )
        self.write({"state": new_state})

    def _cancel_with_reason(self, reason):
        """Cancel the documents and keep the reason on the record and in chatter."""
        self.action_cancel()
        self.cancel_reason = reason
        for document in self:
            document.message_post(body=self.env._("Cancelled: %s", reason))
