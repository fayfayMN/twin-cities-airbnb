# =====================================================================
# TRACK B - STEP 3/4: EDA in R (tidyverse + ggplot2)
#
# Reads the SAME cleaned files Python produced (outputs/listings_clean.csv,
# calendar_daily.csv). Cleaning was done ONCE in Python; here we only analyze,
# so any difference you see vs Track A is language/plotting, not data.
#
# Run:  Rscript R/01_eda.R      (run from the project root)
# Needs: install.packages(c("tidyverse","scales"))
# =====================================================================
suppressPackageStartupMessages({
  library(tidyverse)
  library(scales)
})

out_dir <- file.path("outputs")
fig_dir <- file.path(out_dir, "figures")
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

listings <- read_csv(file.path(out_dir, "listings_clean.csv"),
                     show_col_types = FALSE)
daily    <- read_csv(file.path(out_dir, "calendar_daily.csv"),
                     show_col_types = FALSE)

ggsave2 <- function(name, plot, w = 9, h = 5)
  ggsave(file.path(fig_dir, name), plot, width = w, height = h, dpi = 130)

# ---- Q1: price distribution (log scale) ----------------------------
p1 <- listings %>%
  filter(price > 0) %>%
  ggplot(aes(price)) +
  geom_histogram(bins = 50, fill = "darkorange") +
  scale_x_log10(labels = dollar) +
  labs(title = "Nightly price (log scale) — right-skewed",
       x = "price (log10)", y = "listings") +
  theme_minimal()
ggsave2("R_01_price_distribution.png", p1)

# ---- Q2: price by room type ----------------------------------------
p2 <- listings %>%
  filter(price < quantile(price, 0.98, na.rm = TRUE)) %>%
  mutate(room_type = fct_reorder(room_type, price, median, na.rm = TRUE)) %>%
  ggplot(aes(room_type, price)) +
  geom_boxplot(fill = "steelblue", alpha = 0.7) +
  labs(title = "Price by room type", x = NULL, y = "nightly price") +
  theme_minimal() + theme(axis.text.x = element_text(angle = 20, hjust = 1))
ggsave2("R_02_price_by_roomtype.png", p2)

# ---- Q3: median price by county ------------------------------------
p3 <- listings %>%
  group_by(neighbourhood_cleansed) %>%
  summarise(n = n(), median_price = median(price, na.rm = TRUE)) %>%
  slice_max(n, n = 12) %>%
  ggplot(aes(median_price, fct_reorder(neighbourhood_cleansed, median_price))) +
  geom_col(fill = "steelblue") +
  scale_x_continuous(labels = dollar) +
  labs(title = "Median nightly price by county (top 12 by count)",
       x = "median price", y = NULL) +
  theme_minimal()
ggsave2("R_03_price_by_county.png", p3)

# ---- Q4: Superhost effect on revenue -------------------------------
p4 <- listings %>%
  filter(!is.na(host_is_superhost), !is.na(estimated_revenue_l365d),
         estimated_revenue_l365d < quantile(estimated_revenue_l365d, 0.97, na.rm = TRUE)) %>%
  ggplot(aes(host_is_superhost, estimated_revenue_l365d)) +
  geom_boxplot(fill = "seagreen", alpha = 0.7) +
  scale_y_continuous(labels = dollar) +
  labs(title = "Estimated annual revenue: Superhost vs not",
       x = "is superhost", y = "est. revenue / yr") +
  theme_minimal()
ggsave2("R_04_superhost_revenue.png", p4)

# ---- Q5: amenity revenue lift --------------------------------------
amen_lift <- listings %>%
  select(estimated_revenue_l365d, starts_with("amen_")) %>%
  pivot_longer(starts_with("amen_"), names_to = "amenity", values_to = "has") %>%
  filter(!is.na(estimated_revenue_l365d)) %>%
  group_by(amenity, has) %>%
  summarise(med = median(estimated_revenue_l365d), .groups = "drop") %>%
  pivot_wider(names_from = has, values_from = med) %>%
  mutate(amenity = str_remove(amenity, "amen_"),
         lift = `TRUE` - `FALSE`)

p5 <- amen_lift %>%
  ggplot(aes(lift, fct_reorder(amenity, lift), fill = lift > 0)) +
  geom_col() +
  geom_vline(xintercept = 0) +
  scale_x_continuous(labels = dollar) +
  scale_fill_manual(values = c("crimson", "seagreen"), guide = "none") +
  labs(title = "Median revenue lift when a listing HAS each amenity",
       x = "$/yr lift", y = NULL) +
  theme_minimal()
ggsave2("R_05_amenity_premium.png", p5)

# ---- Q6: forward seasonality ---------------------------------------
p6 <- daily %>%
  mutate(date = as.Date(date), blocked = 1 - available_rate) %>%
  ggplot(aes(date, blocked)) +
  geom_line(color = "purple") +
  labs(title = "Share of listings blocked/booked by date (upper-bound demand)",
       x = NULL, y = "blocked share") +
  theme_minimal()
ggsave2("R_06_seasonality.png", p6, w = 11, h = 4)

cat("R EDA done. Figures with R_ prefix in outputs/figures/\n")
