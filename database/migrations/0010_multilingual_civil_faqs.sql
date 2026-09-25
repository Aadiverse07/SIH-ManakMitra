-- Phase 16: Civil-engineering FAQ seed used by ManakMitra chat.
-- The chat layer now detects English, Hindi, Bengali, Tamil, Marathi and
-- Hinglish. These canonical FAQ records are stored in English; multilingual
-- questions that are not deterministic FAQ matches continue through the
-- multilingual AI pipeline and are answered in the detected user language.

with new_faqs(question, answer, category) as (
  values
    ('What is concrete mix design.',
     'Concrete mix design is the process of selecting suitable concrete ingredients and deciding their proportions so that the concrete achieves the required strength, workability, durability and economy. The main ingredients are cementitious material, water, fine aggregate, coarse aggregate and, when required, admixtures. The final proportions depend on project requirements, material properties and the applicable design method or standard.',
     'civil_engineering_normal'),

    ('Different types of cement (at least 10).',
     'Common types of cement include: (1) Ordinary Portland Cement (OPC 33 grade), (2) OPC 43 grade, (3) OPC 53 grade, (4) Portland Pozzolana Cement (PPC), (5) Portland Slag Cement (PSC), (6) Rapid Hardening Cement, (7) Low Heat Cement, (8) Sulphate Resisting Cement, (9) White Cement, (10) Hydrophobic Cement, (11) High Alumina Cement, (12) Masonry Cement, (13) Air-Entraining Cement and (14) Super Sulphated Cement. Their suitability depends on exposure conditions and the applicable specification.',
     'civil_engineering_normal'),

    ('What is Bunker.',
     'In civil and structural engineering, a bunker is a storage structure or container used for bulk materials such as coal, cement, grain, ore or aggregates. It usually has vertical or steeply inclined sides and a hopper-shaped bottom so that material can discharge by gravity. Bunkers are designed for the pressures produced by the stored material as well as structural loads.',
     'civil_engineering_normal'),

    ('What is Dam.',
     'A dam is a barrier constructed across a river, stream or other watercourse to obstruct, store, control or divert water. Dams may be used for water supply, irrigation, flood control, hydropower, navigation and recreation. Common structural types include gravity, arch, buttress, earth-fill and rock-fill dams.',
     'civil_engineering_normal'),

    ('What is Bitumen.',
     'Bitumen is a dark, viscous, cementitious hydrocarbon material obtained mainly from petroleum refining. In road construction it acts as the binder in bituminous or asphalt mixtures, coating aggregate particles and providing cohesion, waterproofing and flexibility. Its grade is selected according to pavement design, climate and specification requirements.',
     'civil_engineering_normal'),

    ('What is Pavement design.',
     'Pavement design is the process of determining the type, materials and thicknesses of pavement layers so that a road can safely carry expected traffic during its design life while controlling distress and maintaining serviceability. The design considers traffic loading, subgrade strength, material properties, drainage, climate, reliability and the selected flexible or rigid pavement design method.',
     'civil_engineering_normal'),

    ('What is IRC (Indian Roads Congress).',
     'The Indian Roads Congress (IRC) is the apex technical body of highway engineers in India. It publishes codes, guidelines, specifications and recommended practices for the planning, design, construction, operation and maintenance of roads, bridges and related transportation infrastructure. Project requirements should use the specific IRC document and edition applicable to the work.',
     'civil_engineering_normal'),

    ('What is truss.',
     'A truss is a structural framework made mainly of straight members connected at joints to form triangular units. Under the ideal truss assumption, loads are applied at the joints and the members primarily carry axial tension or compression. Trusses are widely used in roofs, bridges, towers and long-span structures because they can carry loads efficiently with relatively low self-weight.',
     'civil_engineering_normal'),

    ('What is foundation.',
     'A foundation is the lowest part of a structure that safely transfers loads from the superstructure to the supporting soil or rock. It must provide adequate bearing capacity and stability while keeping total and differential settlement within acceptable limits. Foundations are broadly classified as shallow and deep foundations.',
     'civil_engineering_normal'),

    ('Different types of foundation.',
     'Foundations are broadly divided into two groups: shallow foundations and deep foundations. Shallow foundations transfer loads to soil close to the ground surface and include isolated, strip, combined, strap and raft foundations. Deep foundations transfer loads to deeper, stronger strata or develop resistance along their depth and include piles, piers/drilled shafts and well or caisson foundations.',
     'civil_engineering_normal'),

    ('Different types of shallow foundation.',
     'Common shallow foundations are: (1) isolated or pad footing, (2) strip or continuous/wall footing, (3) combined footing, (4) strap or cantilever footing, (5) raft or mat foundation and (6) grillage foundation. The choice depends on column or wall loads, spacing, soil bearing capacity, settlement limits, property boundaries and construction conditions.',
     'civil_engineering_normal'),

    ('Different types of deep foundation.',
     'Common deep foundations include: (1) pile foundations, such as end-bearing, friction or combined-action piles; (2) drilled shafts or piers; (3) well foundations, commonly used for bridge substructures; and (4) caisson foundations. Special deep elements such as barrettes or diaphragm-wall foundation elements may also be used for heavy loads and difficult ground conditions.',
     'civil_engineering_normal'),

    ('What is the major difference between one way slab and two way slab.',
     'The major difference is the direction in which the slab primarily bends and transfers load. A one-way slab mainly spans and bends in one direction, so its main flexural reinforcement is provided along the shorter span. A two-way slab bends and transfers load in both principal directions, so main reinforcement is required in both directions. For a slab supported on four sides, the longer-span to shorter-span ratio Ly/Lx is commonly used as an initial classification: greater than 2 generally indicates one-way action, while 2 or less generally indicates two-way action, subject to the actual support conditions and design code.',
     'civil_engineering_difficult'),

    ('What is prestressed concrete.',
     'Prestressed concrete is concrete in which deliberate compressive stresses are introduced, usually by tensioning high-strength steel tendons, so that tensile stresses caused by service loads are reduced or counteracted. In pretensioning, tendons are stressed before the concrete is cast and the force is transferred after the concrete gains strength. In post-tensioning, tendons are stressed after the concrete has hardened. Prestressing can increase span capacity, control cracking and reduce deflection.',
     'civil_engineering_difficult'),

    ('What is the formula to find the superelevation.',
     'For highway curves, the basic equilibrium relation is e + f = V^2/(127 R), where e is superelevation as a decimal, f is the lateral friction factor, V is speed in km/h and R is curve radius in metres. A commonly taught IRC design relation for calculating superelevation by neglecting side friction at 75% of design speed is e = V^2/(225 R). The allowable value of e and the exact design procedure must follow the applicable IRC specification.',
     'civil_engineering_difficult'),

    ('How to find a gross area in bolt.',
     'For a bolt with nominal shank diameter d, the gross cross-sectional area of the unthreaded shank is Ag = pi*d^2/4. If the critical section passes through the threads, the effective tensile or threaded area is smaller than the gross shank area and should be taken from the applicable bolt/thread specification rather than using the gross-area formula.',
     'civil_engineering_difficult'),

    ('Formula for area of steel? (Ast = pi/4 x d^2)',
     'For one circular reinforcing bar of diameter d, the cross-sectional area is A = pi*d^2/4. For n bars of the same diameter, the total steel area is Ast = n*pi*d^2/4. Use consistent units; for example, if d is in millimetres, Ast is obtained in square millimetres.',
     'civil_engineering_difficult'),

    ('How can I calculate the bending moment?',
     'Bending moment at a section is calculated by taking the algebraic sum of the moments of external forces about that section after drawing the loading and support reactions. The exact expression depends on the beam and loading. Common maximum values are: simply supported beam with a central point load W, Mmax = W*L/4; simply supported beam with a full-span UDL w, Mmax = w*L^2/8; cantilever with an end point load W, Mmax = W*L; and cantilever with a full-span UDL w, Mmax = w*L^2/2. Use the project sign convention and actual load combinations for design.',
     'civil_engineering_difficult'),

    ('What is single wheel load.',
     'A single wheel load is the load transmitted to the pavement or supporting surface by one vehicle wheel at its contact area. In pavement analysis it may be idealised as a concentrated load or as a uniformly distributed pressure over a tyre-contact area. It is used to evaluate stresses, strains and deflections, while axle and wheel-group effects must also be considered in practical pavement design.',
     'civil_engineering_difficult')
)
insert into faqs (question, answer, category)
select n.question, n.answer, n.category
from new_faqs n
where not exists (
  select 1 from faqs f where lower(trim(f.question)) = lower(trim(n.question))
);
