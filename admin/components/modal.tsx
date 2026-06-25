"use client";

import {X} from "lucide-react";

export function Modal({title, children, onClose}: {title: string; children: React.ReactNode; onClose: () => void}) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section className="modal" role="dialog" aria-modal="true" aria-label={title}>
      <header className="modal-header"><h2>{title}</h2><button className="button icon-button" aria-label="Close" onClick={onClose}><X size={16} /></button></header>
      <div className="modal-body">{children}</div>
    </section>
  </div>;
}
