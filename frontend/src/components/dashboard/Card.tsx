import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

function Card({ title, children, className }: CardProps) {
  return (
    <section className={`dash-card ${className ?? ""}`.trim()}>
      {title && <h3 className="dash-card-title">{title}</h3>}
      {children}
    </section>
  );
}

export default Card;
