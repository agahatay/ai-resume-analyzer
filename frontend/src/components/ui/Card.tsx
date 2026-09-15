import type { ReactNode } from "react";
import "./ui.css";

interface CardProps {
  title?: string;
  titleLevel?: "h2" | "h3";
  children: ReactNode;
  className?: string;
}

function Card({ title, titleLevel = "h3", children, className }: CardProps) {
  const Heading = titleLevel;
  return (
    <section className={`ui-card ${className ?? ""}`.trim()}>
      {title && <Heading className="ui-card-title">{title}</Heading>}
      {children}
    </section>
  );
}

export default Card;
