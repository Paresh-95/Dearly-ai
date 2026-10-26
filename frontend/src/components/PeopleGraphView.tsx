import { useState } from "react";
import { Person, Persona } from "../api";
import PersonaAvatar from "./PersonaAvatar";

const NODE_COLORS = ["var(--plum)", "var(--gold)", "var(--sage)", "var(--rose)"];
const YOU_NODE_ID = "__you__";

const SIZE = 640;
const CENTER = SIZE / 2;
const ORBIT_RADIUS = 220;
const CENTER_NODE_RADIUS = 46;
const PERSON_NODE_RADIUS = 32;

export default function PeopleGraphView({ persona, people }: { persona: Persona; people: Person[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // The user's own relationship to the persona is always the first
  // connection in this graph — it exists the moment a persona does, no
  // "Add a person" step required, so it's shown automatically rather than
  // depending on the People list being populated.
  const nodes = [
    {
      id: YOU_NODE_ID,
      name: "You",
      edgeLabel: persona.user_relationship,
      isYou: true as const,
      person: null as Person | null,
    },
    ...people.map((person) => ({
      id: person.id,
      name: person.name,
      edgeLabel: person.relation_to_persona,
      isYou: false as const,
      person,
    })),
  ];

  const positions = nodes.map((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    return {
      node,
      x: CENTER + ORBIT_RADIUS * Math.cos(angle),
      y: CENTER + ORBIT_RADIUS * Math.sin(angle),
      color: node.isYou ? "var(--ink)" : NODE_COLORS[(i - 1) % NODE_COLORS.length],
    };
  });

  const selected = nodes.find((n) => n.id === selectedId) ?? null;

  return (
    <div className="people-graph">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="people-graph__svg" role="img" aria-label={`${persona.name}'s relationship graph`}>
        {positions.map(({ node, x, y }) => {
          const midX = CENTER + (x - CENTER) * 0.56;
          const midY = CENTER + (y - CENTER) * 0.56;
          const isSelected = node.id === selectedId;
          return (
            <g key={`edge-${node.id}`}>
              <line
                x1={CENTER}
                y1={CENTER}
                x2={x}
                y2={y}
                className={`people-graph__edge ${isSelected ? "people-graph__edge--active" : ""}`}
              />
              {node.edgeLabel && (
                <g transform={`translate(${midX}, ${midY})`}>
                  <rect
                    x={-(node.edgeLabel.length * 3.6 + 8)}
                    y={-10}
                    width={node.edgeLabel.length * 7.2 + 16}
                    height={20}
                    rx={10}
                    className="people-graph__edge-label-bg"
                  />
                  <text textAnchor="middle" dy="0.32em" className="people-graph__edge-label">
                    {node.edgeLabel}
                  </text>
                </g>
              )}
            </g>
          );
        })}

        <foreignObject x={CENTER - CENTER_NODE_RADIUS} y={CENTER - CENTER_NODE_RADIUS} width={CENTER_NODE_RADIUS * 2} height={CENTER_NODE_RADIUS * 2}>
          <div className="people-graph__center-avatar">
            <PersonaAvatar persona={persona} size={CENTER_NODE_RADIUS * 2} />
          </div>
        </foreignObject>
        <text x={CENTER} y={CENTER + CENTER_NODE_RADIUS + 20} textAnchor="middle" className="people-graph__center-label">
          {persona.name}
        </text>

        {positions.map(({ node, x, y, color }) => {
          const isSelected = node.id === selectedId;
          return (
            <g
              key={node.id}
              transform={`translate(${x}, ${y})`}
              className="people-graph__node"
              onClick={() => setSelectedId(isSelected ? null : node.id)}
              tabIndex={0}
              role="button"
              aria-label={`${node.name}${node.edgeLabel ? `, ${node.edgeLabel}` : ""}`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") setSelectedId(isSelected ? null : node.id);
              }}
            >
              <circle
                r={PERSON_NODE_RADIUS}
                style={{ fill: color }}
                className={`people-graph__node-circle ${isSelected ? "people-graph__node-circle--active" : ""}`}
              />
              <text textAnchor="middle" dy="0.34em" className="people-graph__node-initial" style={node.isYou ? { fontSize: "0.85rem" } : undefined}>
                {node.isYou ? "You" : node.name.trim().slice(0, 1).toUpperCase() || "?"}
              </text>
              <text y={PERSON_NODE_RADIUS + 20} textAnchor="middle" className="people-graph__node-label">
                {node.name}
              </text>
            </g>
          );
        })}
      </svg>

      {people.length === 0 && (
        <p className="empty-note">Nobody else added yet — switch to list view to add a person.</p>
      )}

      {selected && (
        <div className="people-graph__detail">
          <div className="people-graph__detail-header">
            <span className="people-graph__detail-name">{selected.name}</span>
            <button className="btn btn--quiet btn--sm" onClick={() => setSelectedId(null)}>
              close
            </button>
          </div>
          {selected.isYou ? (
            <>
              {persona.user_relationship && (
                <div>
                  {persona.name}'s {persona.user_relationship}
                </div>
              )}
              {persona.relationship_to_user && (
                <div>
                  {persona.name} is your {persona.relationship_to_user}
                </div>
              )}
              <div className="people-graph__detail-notes">Edit this on the Settings tab.</div>
            </>
          ) : (
            <>
              {selected.person?.relation_to_persona && (
                <div>
                  {persona.name}'s {selected.person.relation_to_persona}
                </div>
              )}
              {selected.person?.relation_to_user && <div>Your {selected.person.relation_to_user}</div>}
              {selected.person?.notes && <div className="people-graph__detail-notes">{selected.person.notes}</div>}
            </>
          )}
        </div>
      )}
    </div>
  );
}
